import threading
import uuid

from sqlalchemy import func, select

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.db import SessionLocal
from app.messages.models import Message
from app.messages.service import add_message


def _make_user(db, name: str) -> User:
    user = User(name=name, email=f"{name.lower()}@example.com", password_hash="not-a-real-hash")
    db.add(user)
    db.commit()
    return user


def _make_direct_chat(db, a: User, b: User) -> Chat:
    chat = Chat(kind="direct", direct_key=":".join(sorted([str(a.id), str(b.id)])))
    db.add(chat)
    db.flush()  # gives the chat its id, so the members can point at it
    db.add_all([ChatMember(chat_id=chat.id, user_id=a.id), ChatMember(chat_id=chat.id, user_id=b.id)])
    db.commit()
    return chat


def _message_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Message))


def test_three_messages_get_1_2_3(db):
    ana, ben = _make_user(db, "Ana"), _make_user(db, "Ben")
    chat = _make_direct_chat(db, ana, ben)

    seqs = [add_message(db, chat.id, ana.id, uuid.uuid4(), f"hello {n}")[0].seq for n in range(3)]

    assert seqs == [1, 2, 3]
    db.refresh(chat)
    assert chat.last_seq == 3


def test_same_client_msg_id_twice_gives_one_row(db):
    ana, ben = _make_user(db, "Ana"), _make_user(db, "Ben")
    chat = _make_direct_chat(db, ana, ben)
    client_msg_id = uuid.uuid4()

    first, first_created = add_message(db, chat.id, ana.id, client_msg_id, "hi")
    retry, retry_created = add_message(db, chat.id, ana.id, client_msg_id, "hi")

    assert retry.id == first.id
    assert first_created and not retry_created
    assert _message_count(db) == 1
    db.refresh(chat)
    assert chat.last_seq == 1  # the retry didn't use up a number


def test_two_chats_count_separately(db):
    ana, ben, cara = _make_user(db, "Ana"), _make_user(db, "Ben"), _make_user(db, "Cara")
    with_ben = _make_direct_chat(db, ana, ben)
    with_cara = _make_direct_chat(db, ana, cara)

    add_message(db, with_ben.id, ana.id, uuid.uuid4(), "hi Ben")
    second_to_ben, _ = add_message(db, with_ben.id, ana.id, uuid.uuid4(), "you there?")
    first_to_cara, _ = add_message(db, with_cara.id, ana.id, uuid.uuid4(), "hi Cara")

    assert second_to_ben.seq == 2
    assert first_to_cara.seq == 1


def test_sender_has_read_own_messages(db):
    ana, ben = _make_user(db, "Ana"), _make_user(db, "Ben")
    chat = _make_direct_chat(db, ana, ben)

    for n in range(3):
        add_message(db, chat.id, ana.id, uuid.uuid4(), f"hello {n}")

    def read_up_to(user):
        return db.get(ChatMember, (chat.id, user.id)).read_up_to

    db.expire_all()  # read the bookmarks fresh from the database
    assert read_up_to(ana) == 3  # Ana's own messages are never unread for her
    assert read_up_to(ben) == 0  # Ben hasn't read anything yet


def test_two_senders_at_the_same_moment_get_different_numbers(db):
    ana, ben = _make_user(db, "Ana"), _make_user(db, "Ben")
    chat_id = _make_direct_chat(db, ana, ben).id
    sender_ids = [ana.id, ben.id]
    start_together = threading.Barrier(2)
    seqs = []

    def send(sender_id):
        # Each sender gets its own database connection, like two separate requests.
        with SessionLocal() as own_db:
            start_together.wait()  # both threads send at the same moment
            message, _ = add_message(own_db, chat_id, sender_id, uuid.uuid4(), "at the same time")
            seqs.append(message.seq)

    threads = [threading.Thread(target=send, args=(sender_id,)) for sender_id in sender_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Two numbers means neither thread hit an error; different numbers means no clash.
    assert sorted(seqs) == [1, 2]

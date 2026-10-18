// Fake data for the screens (T4). The real backend replaces this in T15.
// Every name here is made up (D8).

// Avatar colors: soft tints from docs/design/look.md
export type Tint = "teal" | "purple" | "yellow" | "red"

// sent = one grey tick, delivered = two grey ticks, read = two teal ticks
export type Tick = "sent" | "delivered" | "read"

export type Person = {
  id: string
  name: string
  tint: Tint
}

export type Message = {
  id: string
  senderId: string
  text: string
  time: string
  tick?: Tick // only on my messages
}

export type FileGroup = {
  count: number
  size: string
}

export type SharedFiles = {
  all: number
  links: number
  documents: FileGroup
  photos: FileGroup
  movies: FileGroup
  other: FileGroup
}

export type Chat = {
  id: string
  name: string
  tint: Tint
  isGroup: boolean
  memberCount: number
  day?: string // shown in the chat list instead of a time when the last message is not from today
  unread: number
  typingId?: string // the person typing right now, if anyone
  files: SharedFiles
  messages: Message[]
}

export const me: Person = { id: "me", name: "Kiran Rao", tint: "teal" }

export const people: Record<string, Person> = {
  me,
  mira: { id: "mira", name: "Mira Patel", tint: "purple" },
  theo: { id: "theo", name: "Theo Ruiz", tint: "teal" },
  sam: { id: "sam", name: "Sam Okafor", tint: "yellow" },
  lena: { id: "lena", name: "Lena Fischer", tint: "red" },
  nadia: { id: "nadia", name: "Nadia Karim", tint: "teal" },
  omar: { id: "omar", name: "Omar Haddad", tint: "purple" },
  priya: { id: "priya", name: "Priya Nair", tint: "red" },
  jonas: { id: "jonas", name: "Jonas Berg", tint: "yellow" },
  aiko: { id: "aiko", name: "Aiko Tanaka", tint: "purple" },
  leo: { id: "leo", name: "Leo Martins", tint: "teal" },
  zara: { id: "zara", name: "Zara Ahmed", tint: "yellow" },
  ben: { id: "ben", name: "Ben Carter", tint: "red" },
}

export const chats: Chat[] = [
  {
    id: "hike",
    name: "Weekend hike",
    tint: "teal",
    isGroup: true,
    memberCount: 8,
    unread: 0,
    typingId: "mira",
    files: {
      all: 184,
      links: 37,
      documents: { count: 92, size: "148MB" },
      photos: { count: 61, size: "356MB" },
      movies: { count: 4, size: "240MB" },
      other: { count: 27, size: "88MB" },
    },
    messages: [
      { id: "h1", senderId: "theo", time: "10:52 AM", text: "Morning all! Are we still on for Saturday?" },
      { id: "h2", senderId: "mira", time: "10:54 AM", text: "Yes! I checked the weather, sunny all day" },
      { id: "h3", senderId: "me", time: "10:55 AM", text: "Great. Which trail are we doing?", tick: "read" },
      { id: "h4", senderId: "sam", time: "10:58 AM", text: "I vote for the lake loop. About 12 km" },
      { id: "h5", senderId: "lena", time: "11:01 AM", text: "@Sam that one is steep near the end" },
      { id: "h6", senderId: "sam", time: "11:02 AM", text: "Steep, but the view is worth it" },
      { id: "h7", senderId: "theo", time: "11:05 AM", text: "I can drive. I have room for three more" },
      { id: "h8", senderId: "me", time: "11:08 AM", text: "Count me in for a seat, @Theo", tick: "read" },
      { id: "h9", senderId: "mira", time: "11:12 AM", text: "Let's meet at the station at 7" },
      { id: "h10", senderId: "me", time: "11:15 AM", text: "Works for me. I'll bring snacks", tick: "delivered" },
    ],
  },
  {
    id: "lena",
    name: "Lena Fischer",
    tint: "red",
    isGroup: false,
    memberCount: 2,
    unread: 2,
    files: {
      all: 23,
      links: 9,
      documents: { count: 15, size: "31MB" },
      photos: { count: 6, size: "18MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 2, size: "3MB" },
    },
    messages: [
      { id: "l1", senderId: "me", time: "9:40 AM", text: "Hi Lena, did you get a chance to look at the draft?", tick: "read" },
      { id: "l2", senderId: "lena", time: "9:52 AM", text: "Not yet, sorry! Busy morning" },
      { id: "l3", senderId: "lena", time: "9:53 AM", text: "I'll read it before lunch" },
      { id: "l4", senderId: "me", time: "9:55 AM", text: "No rush. The deadline is Friday", tick: "read" },
      { id: "l5", senderId: "lena", time: "10:41 AM", text: "Okay, I read it. Looks good overall" },
      { id: "l6", senderId: "me", time: "10:44 AM", text: "Any parts you'd change?", tick: "read" },
      { id: "l7", senderId: "lena", time: "10:50 AM", text: "The intro is a bit long. Maybe cut the first paragraph" },
      { id: "l8", senderId: "lena", time: "11:14 AM", text: "Also, I made some notes" },
      { id: "l9", senderId: "lena", time: "11:15 AM", text: "I will send the document soon" },
    ],
  },
  {
    id: "theo",
    name: "Theo Ruiz",
    tint: "teal",
    isGroup: false,
    memberCount: 2,
    unread: 0,
    files: {
      all: 12,
      links: 4,
      documents: { count: 2, size: "1MB" },
      photos: { count: 8, size: "24MB" },
      movies: { count: 1, size: "45MB" },
      other: { count: 1, size: "1MB" },
    },
    messages: [
      { id: "t1", senderId: "theo", time: "9:12 AM", text: "Did you watch the match last night?" },
      { id: "t2", senderId: "me", time: "9:20 AM", text: "Only the second half. What a finish!", tick: "read" },
      { id: "t3", senderId: "theo", time: "9:21 AM", text: "That last goal was unreal" },
      { id: "t4", senderId: "me", time: "9:25 AM", text: "I still can't believe the keeper missed it", tick: "read" },
      { id: "t5", senderId: "theo", time: "9:40 AM", text: "Want to play five-a-side on Sunday?" },
      { id: "t6", senderId: "me", time: "9:58 AM", text: "Sure, what time?", tick: "read" },
      { id: "t7", senderId: "theo", time: "10:02 AM", text: "Around 4, at the usual place" },
      { id: "t8", senderId: "me", time: "10:05 AM", text: "Perfect, see you there", tick: "read" },
    ],
  },
  {
    id: "sam",
    name: "Sam Okafor",
    tint: "yellow",
    isGroup: false,
    memberCount: 2,
    day: "15.09",
    unread: 0,
    files: {
      all: 7,
      links: 12,
      documents: { count: 5, size: "9MB" },
      photos: { count: 2, size: "4MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "s1", senderId: "sam", time: "4:10 PM", text: "Hey, are you going to the meetup on Thursday?" },
      { id: "s2", senderId: "me", time: "4:12 PM", text: "Thinking about it. Is it about system design again?", tick: "read" },
      { id: "s3", senderId: "sam", time: "4:15 PM", text: "Yes, someone is talking about message queues" },
      { id: "s4", senderId: "me", time: "4:16 PM", text: "Oh nice, that's what I'm learning right now", tick: "read" },
      { id: "s5", senderId: "sam", time: "4:20 PM", text: "Then you have to come" },
      { id: "s6", senderId: "sam", time: "4:21 PM", text: "I can save you a seat" },
      { id: "s7", senderId: "me", time: "4:30 PM", text: "Deal. Should I bring anything?", tick: "read" },
      { id: "s8", senderId: "sam", time: "4:31 PM", text: "Just questions. Come early, it fills up fast" },
    ],
  },
  {
    id: "nadia",
    name: "Nadia Karim",
    tint: "teal",
    isGroup: false,
    memberCount: 2,
    day: "14.09",
    unread: 1,
    files: {
      all: 48,
      links: 3,
      documents: { count: 1, size: "2MB" },
      photos: { count: 44, size: "212MB" },
      movies: { count: 3, size: "96MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "n1", senderId: "me", time: "6:02 PM", text: "Hi Nadia! How was the trip?", tick: "read" },
      { id: "n2", senderId: "nadia", time: "6:30 PM", text: "Amazing! The food was so good" },
      { id: "n3", senderId: "nadia", time: "6:31 PM", text: "I took so many photos" },
      { id: "n4", senderId: "me", time: "6:33 PM", text: "Send them over, I want to see", tick: "read" },
      { id: "n5", senderId: "nadia", time: "6:40 PM", text: "Will do once I sort them" },
      { id: "n6", senderId: "me", time: "6:42 PM", text: "Where should I go first if I visit?", tick: "read" },
      { id: "n7", senderId: "nadia", time: "6:50 PM", text: "The old town, for sure. Go early in the morning" },
      { id: "n8", senderId: "nadia", time: "7:05 PM", text: "We need to plan a trip together next year" },
    ],
  },
  {
    id: "omar",
    name: "Omar Haddad",
    tint: "purple",
    isGroup: false,
    memberCount: 2,
    day: "12.09",
    unread: 0,
    files: {
      all: 16,
      links: 6,
      documents: { count: 14, size: "52MB" },
      photos: { count: 1, size: "2MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 1, size: "1MB" },
    },
    messages: [
      { id: "o1", senderId: "omar", time: "2:00 PM", text: "Can you check the slides before the call?" },
      { id: "o2", senderId: "me", time: "2:05 PM", text: "Sure, send them over", tick: "read" },
      { id: "o3", senderId: "omar", time: "2:06 PM", text: "Sent. Slide 4 needs the new numbers" },
      { id: "o4", senderId: "me", time: "2:20 PM", text: "Updated slide 4. The chart looks better now", tick: "read" },
      { id: "o5", senderId: "omar", time: "2:22 PM", text: "Thanks! That's much clearer" },
      { id: "o6", senderId: "omar", time: "2:23 PM", text: "Can you also fix the title on slide 1?" },
      { id: "o7", senderId: "me", time: "2:30 PM", text: "Done. Anything else?", tick: "delivered" },
      { id: "o8", senderId: "me", time: "2:31 PM", text: "I'll be offline for an hour", tick: "sent" },
    ],
  },
  {
    id: "priya",
    name: "Priya Nair",
    tint: "red",
    isGroup: false,
    memberCount: 2,
    day: "11.09",
    unread: 0,
    files: {
      all: 9,
      links: 5,
      documents: { count: 3, size: "6MB" },
      photos: { count: 6, size: "15MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "p1", senderId: "priya", time: "8:15 AM", text: "Good morning! Are you coming to the gym today?" },
      { id: "p2", senderId: "me", time: "8:20 AM", text: "Yes, around 6 in the evening", tick: "read" },
      { id: "p3", senderId: "priya", time: "8:21 AM", text: "Great, let's do legs together" },
      { id: "p4", senderId: "me", time: "8:22 AM", text: "Oh no. Okay, fine", tick: "read" },
      { id: "p5", senderId: "priya", time: "8:25 AM", text: "You'll thank me later" },
      { id: "p6", senderId: "me", time: "5:50 PM", text: "Running 10 minutes late, sorry", tick: "read" },
      { id: "p7", senderId: "priya", time: "5:52 PM", text: "No problem, I'll start warming up" },
      { id: "p8", senderId: "me", time: "7:30 PM", text: "That was tough. See you Thursday", tick: "read" },
    ],
  },
  {
    id: "jonas",
    name: "Jonas Berg",
    tint: "yellow",
    isGroup: false,
    memberCount: 2,
    day: "10.09",
    unread: 3,
    files: {
      all: 31,
      links: 14,
      documents: { count: 25, size: "64MB" },
      photos: { count: 4, size: "9MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 2, size: "5MB" },
    },
    messages: [
      { id: "j1", senderId: "me", time: "3:00 PM", text: "Hi Jonas, is the build working on your side?", tick: "read" },
      { id: "j2", senderId: "jonas", time: "3:04 PM", text: "Not yet. Tests fail on my laptop" },
      { id: "j3", senderId: "me", time: "3:05 PM", text: "Did you pull the latest main?", tick: "read" },
      { id: "j4", senderId: "jonas", time: "3:10 PM", text: "That was it. All green now" },
      { id: "j5", senderId: "me", time: "3:11 PM", text: "Nice! Can you review my pull request?", tick: "read" },
      { id: "j6", senderId: "jonas", time: "4:02 PM", text: "Looking at it now" },
      { id: "j7", senderId: "jonas", time: "4:15 PM", text: "Left two small comments" },
      { id: "j8", senderId: "jonas", time: "4:16 PM", text: "Otherwise it looks good to merge" },
    ],
  },
  {
    id: "aiko",
    name: "Aiko Tanaka",
    tint: "purple",
    isGroup: false,
    memberCount: 2,
    day: "08.09",
    unread: 0,
    files: {
      all: 19,
      links: 2,
      documents: { count: 1, size: "1MB" },
      photos: { count: 17, size: "88MB" },
      movies: { count: 1, size: "30MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "a1", senderId: "aiko", time: "7:40 PM", text: "I tried the ramen place you told me about" },
      { id: "a2", senderId: "me", time: "7:45 PM", text: "And? Was it good?", tick: "read" },
      { id: "a3", senderId: "aiko", time: "7:46 PM", text: "Best ramen I've had in this city" },
      { id: "a4", senderId: "aiko", time: "7:46 PM", text: "The line was long though" },
      { id: "a5", senderId: "me", time: "7:50 PM", text: "Go on a weekday, it's much quieter", tick: "read" },
      { id: "a6", senderId: "aiko", time: "7:52 PM", text: "Good tip. Want to go together next week?" },
      { id: "a7", senderId: "me", time: "8:01 PM", text: "Sure, Tuesday works for me", tick: "read" },
      { id: "a8", senderId: "aiko", time: "8:03 PM", text: "Tuesday it is!" },
    ],
  },
  {
    id: "leo",
    name: "Leo Martins",
    tint: "teal",
    isGroup: false,
    memberCount: 2,
    day: "05.09",
    unread: 0,
    files: {
      all: 5,
      links: 8,
      documents: { count: 4, size: "3MB" },
      photos: { count: 1, size: "2MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "le1", senderId: "leo", time: "11:20 AM", text: "Do you still have my charger?" },
      { id: "le2", senderId: "me", time: "11:32 AM", text: "Yes! Sorry, I forgot to bring it back", tick: "read" },
      { id: "le3", senderId: "leo", time: "11:33 AM", text: "No worries. Can you bring it tomorrow?" },
      { id: "le4", senderId: "me", time: "11:35 AM", text: "Sure, I'll put it in my bag now", tick: "read" },
      { id: "le5", senderId: "leo", time: "11:36 AM", text: "Thanks!" },
      { id: "le6", senderId: "me", time: "9:10 AM", text: "I'm at the office. Where are you sitting?", tick: "read" },
      { id: "le7", senderId: "leo", time: "9:12 AM", text: "Third floor, near the window" },
      { id: "le8", senderId: "me", time: "9:13 AM", text: "Coming up now", tick: "delivered" },
    ],
  },
  {
    id: "zara",
    name: "Zara Ahmed",
    tint: "yellow",
    isGroup: false,
    memberCount: 2,
    day: "02.09",
    unread: 0,
    files: {
      all: 11,
      links: 3,
      documents: { count: 7, size: "12MB" },
      photos: { count: 3, size: "8MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 1, size: "1MB" },
    },
    messages: [
      { id: "z1", senderId: "zara", time: "1:05 PM", text: "Happy birthday! 🎉" },
      { id: "z2", senderId: "me", time: "1:20 PM", text: "Thank you so much!", tick: "read" },
      { id: "z3", senderId: "zara", time: "1:21 PM", text: "Any plans for tonight?" },
      { id: "z4", senderId: "me", time: "1:25 PM", text: "Dinner with family, then cake", tick: "read" },
      { id: "z5", senderId: "zara", time: "1:26 PM", text: "Sounds perfect" },
      { id: "z6", senderId: "zara", time: "1:27 PM", text: "Let's celebrate properly at the weekend" },
      { id: "z7", senderId: "me", time: "1:40 PM", text: "Deal. Saturday?", tick: "read" },
      { id: "z8", senderId: "zara", time: "1:41 PM", text: "Saturday works. I'll book a table" },
    ],
  },
  {
    id: "ben",
    name: "Ben Carter",
    tint: "red",
    isGroup: false,
    memberCount: 2,
    day: "28.08",
    unread: 0,
    files: {
      all: 3,
      links: 1,
      documents: { count: 2, size: "2MB" },
      photos: { count: 1, size: "3MB" },
      movies: { count: 0, size: "0MB" },
      other: { count: 0, size: "0MB" },
    },
    messages: [
      { id: "b1", senderId: "ben", time: "10:00 AM", text: "Hi, I'm moving next month" },
      { id: "b2", senderId: "ben", time: "10:01 AM", text: "Do you know a good moving company?" },
      { id: "b3", senderId: "me", time: "10:15 AM", text: "I used one last year. I'll find their number", tick: "read" },
      { id: "b4", senderId: "ben", time: "10:16 AM", text: "That would help a lot" },
      { id: "b5", senderId: "me", time: "10:40 AM", text: "Found it. I'll send it to you by email", tick: "read" },
      { id: "b6", senderId: "ben", time: "10:42 AM", text: "Got it, thanks!" },
      { id: "b7", senderId: "ben", time: "10:43 AM", text: "I'll let you know how it goes" },
      { id: "b8", senderId: "me", time: "10:50 AM", text: "Good luck with the move!", tick: "sent" },
    ],
  },
]

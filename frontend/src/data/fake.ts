// Fake numbers for the side panel's file tiles. Chats and messages are real
// since T15; shared files come in v2 (D8).

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

export const fakeFiles: SharedFiles = {
  all: 23,
  links: 9,
  documents: { count: 15, size: "31MB" },
  photos: { count: 6, size: "18MB" },
  movies: { count: 0, size: "0MB" },
  other: { count: 2, size: "3MB" },
}

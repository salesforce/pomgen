const GREETINGS_LIST = [
    "Hello",
    "Hi",
    "Greetings",
    "Welcome",
    "Howdy",
    "Hey",
];

const NOUNS_LIST = [
    "TypeScript",
    "JavaScript",
    "pnpm",
    "Bazel",
    "Node",
    "npm",
    "Webpack",
    "React",
    "Docker",
    "ESLint",
];

export function getRandomGreetings(): [string, string] {
    const greeting = GREETINGS_LIST[Math.floor(Math.random() * GREETINGS_LIST.length)];
    const noun = NOUNS_LIST[Math.floor(Math.random() * NOUNS_LIST.length)];
    return [greeting, noun];
}


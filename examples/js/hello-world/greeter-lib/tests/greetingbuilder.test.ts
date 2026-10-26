import { GreetingBuilder } from "../src/greetingbuilder";

function assertEqual(actual: string, expected: string): void {
    if (actual !== expected) {
        throw new Error(`expected "${expected}" but got "${actual}"`);
    }
}

const result = new GreetingBuilder()
    .addGreeting("hello")
    .addGreeting("world")
    .build();

assertEqual(result, "hello world");

console.log("greetingbuilder test passed");

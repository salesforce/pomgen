import figlet from "figlet";
import { GreetingBuilder } from "./greetingbuilder";
import { getRandomGreetings } from "greeter-constants";

export default function greet(): string {
    const [first, second] = getRandomGreetings();
    const greeting = new GreetingBuilder()
        .addGreeting(first)
        .addGreeting(second)
        .build();
    return figlet.textSync(greeting);
}

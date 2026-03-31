export class GreetingBuilder {
    private greetings: string[] = [];

    addGreeting(greeting: string): GreetingBuilder {
        this.greetings.push(greeting);
        return this;
    }

    build(): string {
        return this.greetings.join(" ");
    }
}

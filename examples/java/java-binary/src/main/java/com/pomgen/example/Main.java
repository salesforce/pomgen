package com.pomgen.example;

import com.google.common.base.Joiner;

public class Main {
    public static void main(String[] args) {
        String message = Joiner.on(" ").join("Hello", "from", "java_binary", "deploy", "jar!");
        System.out.println(message);
    }
}

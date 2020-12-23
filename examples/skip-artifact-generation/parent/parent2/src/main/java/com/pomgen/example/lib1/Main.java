package com.pomgen.example.lib1;

import java.lang.reflect.Method;

public class Main  {
    public static void main(String[] args) throws Exception {
        System.out.println("Hello Guava at-runtime-only: " + Class.forName("com.google.common.base.Preconditions"));
        System.out.println("Greetings from lib2: " + Class.forName("com.pomgen.example.lib2.Lib2API").getMethod("getGreeting").invoke(null));
    }
}

package com.pomgen.example.lib1;

import com.google.common.base.Preconditions;
import java.lang.reflect.Method;

public class Main  {
    public static void main(String[] args) throws Exception {
        Preconditions.checkNotNull(args);
        System.out.println("Greetings from lib2: " + Class.forName("com.pomgen.example.lib2.Lib2API").getMethod("getGreeting").invoke(null));
    }
}

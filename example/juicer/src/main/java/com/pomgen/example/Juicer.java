package com.pomgen.example;

public class Juicer {

    void makeJuice(Vegetable[] vegetables) {
        System.out.println("Making juice out of " + vegetables.length + " vegetables");
    }

    void makeJuice(Fruit[] fruits) {
        System.out.println("Making juice out of " + fruits.length + " fruits");
    }
}

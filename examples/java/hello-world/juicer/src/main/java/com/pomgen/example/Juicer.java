package com.pomgen.example;

/**
 * A Juicer produces either Vegetable or Fruit juice.
 */
public class Juicer {

    public void makeJuice(Vegetable[] vegetables) {
        System.out.println("Making juice out of " + vegetables.length + " vegetables");
    }

    public void makeJuice(Fruit[] fruits) {
        System.out.println("Making juice out of " + fruits.length + " fruits");
    }
}

package com.pomgen.example;

public class Main {

    public static void main(String[] args) {
        Juicer juicer = new Juicer();
        juicer.makeJuice(new Vegetable[]{new Chard(), new Kale()});
    }
}

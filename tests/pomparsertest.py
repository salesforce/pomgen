"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""

from crawl import pomparser
import unittest

class PomParserTest(unittest.TestCase):

    def test_pretty_print_similar_poms(self):
        """
        Tests that comments and whitespaces are ignored while comparing poms
        """
        pom1 = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <properties>
            <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
    </properties>
            <dependencies>
    <dependency>
            <groupId>net.bytebuddy</groupId>
            <artifactId>byte-buddy</artifactId>
            <version>1.7.9</version>
        </dependency>
    </dependencies>
</project>"""
        pom2 = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    
            <properties>
        <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
</properties>

            <dependencies>
        <!-- This must be ignored -->
    <dependency>
            
            <groupId>net.bytebuddy</groupId>
            <artifactId>byte-buddy</artifactId>
            <version>1.7.9</version>
            <!-- This must be ignored -->
        </dependency>
    </dependencies>
</project>
        """
        self.assertEqual(pomparser.pretty_print(pom1), pomparser.pretty_print(pom2))

    def test_pretty_print_different_poms(self):
        pom1 = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <dependencies>
        <dependency>
            <groupId>net.bytebuddy</groupId>
            <artifactId>byte-buddy</artifactId>
            <version>1.7.9</version>
        </dependency>
    </dependencies>
</project>"""
        pom2 = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <dependencies>
        <dependency>
            <groupId>net.bytebuddy</groupId>
            <artifactId>byte-buddy</artifactId>
            <version>1.9.7</version>
        </dependency>
    </dependencies>
</project>"""
        self.assertNotEqual(pomparser.pretty_print(pom1), pomparser.pretty_print(pom2))

if __name__ == '__main__':
    unittest.main()


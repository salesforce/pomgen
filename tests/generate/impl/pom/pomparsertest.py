"""
Copyright (c) 2018, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import generate.impl.pom.pomparser as pomparser
import unittest


class PomParserTest(unittest.TestCase):

    def test_format_for_comparison__basic(self):
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
             <dependencies>

        <!-- remove me, spaces below too -->


        <dependency>
            <artifactId>a1</artifactId>
        </dependency>
    </dependencies>
</project>"""

        expected_pom = """<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies>
    <dependency>
      <artifactId>a1</artifactId>
    </dependency>
  </dependencies>
</project>
"""
        self.assertEqual(expected_pom, pomparser.format_for_comparison(pom))

    def test_format_for_comparison__removes_root_description(self):
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <description>
        this will be removed
    </description>
    <dependencies>
        <dependency>
            <artifactId>a1</artifactId>
        </dependency>
    </dependencies>
</project>"""

        expected_pom = """<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies>
    <dependency>
      <artifactId>a1</artifactId>
    </dependency>
  </dependencies>
</project>
"""
        self.assertEqual(expected_pom, pomparser.format_for_comparison(pom))

    def test_format_for_comparison__does_not_remove_nested_description(self):
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <dependencies>
        <description>
          this will not be removed
        </description>
        <dependency>
            <artifactId>a1</artifactId>
        </dependency>
    </dependencies>
</project>"""

        expected_pom = """<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies>
    <description>
          this will not be removed
        </description>
    <dependency>
      <artifactId>a1</artifactId>
    </dependency>
  </dependencies>
</project>
"""
        self.assertEqual(expected_pom, pomparser.format_for_comparison(pom))

    def test_format_for_comparison__similar_poms(self):
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

        self.assertEqual(pomparser.format_for_comparison(pom1), pomparser.format_for_comparison(pom2))

    def test_format_for_comparison__different_poms(self):
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

        self.assertNotEqual(pomparser.format_for_comparison(pom1), pomparser.format_for_comparison(pom2))

    def test_parse_description_metadata__basic(self):
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <description>
        <![CDATA[
            commit: abc123
            poppy.manifest-checksum: f3c44d17deddac4f8e55a34a2ad3ca18c75121cb
        ]]>
    </description>
</project>"""

        expected_metadata = {
            "commit": "abc123",
            "poppy.manifest-checksum": "f3c44d17deddac4f8e55a34a2ad3ca18c75121cb",
        }
        self.assertEqual(expected_metadata, pomparser.parse_description_metadata(pom))

    def test_parse_description_metadata__no_namespace(self):
        pom = """<project>
    <description>
        info: this is a cool description
    </description>
</project>"""

        expected_metadata = {"info": "this is a cool description"}
        self.assertEqual(expected_metadata, pomparser.parse_description_metadata(pom))

    def test_parse_description_metadata__value_contains_colon(self):
        pom = """<project>
    <description>
        <![CDATA[
            url: http://example.com?a=1&b=2
        ]]>
    </description>
</project>"""

        expected_metadata = {"url": "http://example.com?a=1&b=2"}
        self.assertEqual(expected_metadata, pomparser.parse_description_metadata(pom))

    def test_parse_description_metadata__no_description_element(self):
        pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <dependencies>
        <dependency>
            <artifactId>a1</artifactId>
        </dependency>
    </dependencies>
</project>"""

        self.assertEqual({}, pomparser.parse_description_metadata(pom))

    def test_parse_description_metadata__empty_description_element(self):
        pom = """<project>
    <description></description>
</project>"""

        self.assertEqual({}, pomparser.parse_description_metadata(pom))

    def test_parse_description_metadata__content_not_key_value_lines(self):
        pom = """<project>
    <description>
        <![CDATA[
            this is just a plain description without colons
        ]]>
    </description>
</project>"""

        self.assertEqual({}, pomparser.parse_description_metadata(pom))


if __name__ == '__main__':
    unittest.main()


# Saxon-HE (vendored)

`saxon-he-9.9.1-8.jar` — Saxon-HE 9.9.1.8, the free/open-source ("Home Edition") XSLT/XQuery
processor from Saxonica, used to run `oxygen-framework/lassberg/xslt/*.xsl` from the command line
(see `.claude/skills/build-website/`). Licensed under the Mozilla Public License 2.0
(https://www.saxonica.com/html/products/license-he.html).

9.9.1.8 was chosen over the newer 12.x series because 12.x split the XML catalog resolver into a
separate `org.xmlresolver` dependency, which isn't vendored here; 9.9.1.8 is a single
self-contained jar and needs only a JRE.

Requires `java` on `PATH`. No other setup.

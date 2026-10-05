#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kept as a short way in (2.21.0): the module folders are now checked as part of the whole course folder, to the
classroom system's own rules (L45) - check_course_package.py does it, and ends with the classroom's own importer.

    check_module_folder.py <master folder | course folder | course\\modules folder>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_course_package  # noqa: E402

if __name__ == "__main__":
    sys.exit(check_course_package.main())

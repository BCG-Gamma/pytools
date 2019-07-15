# yield-engine

You can find the API reference of yield-engine [here](https://git.sourceai.io/pages/schneider-joerg/yield-engine/).

##### Table of Contents  

<!-- TOC depthFrom:2 -->

- [1. Setup](#1-setup)
    - [1.1 Python Environment](#11-python-environment)
    - [1.2 Pytest](#12-pytest)
    - [1.3 Sphinx Documentation](#13-sphinx-documentation)

## 1. Setup
### 1.1 Python Environment
There is a `environment.yml` provided in the project root folder, which you can use with Anaconda to set up a virtualenv for yieldengine.
### 1.2 Pytest
Simply run `pytest tests/` from the project root folder (or use the PyCharm testrunner). The execution of pytest with coverage can be triggered using `pytest --cov=yieldengine tests/`.
### 1.3 Sphinx Documentation
The generated Sphinx documentation of yieldengine is located at _/docs_. To build the documentation, ensure you have the Python packages `sphinx=2.0.1` and `sphinx_rtd_theme=0.4.3` installed, which we have purposely not included into the `environment.yml`. To update, simply run `make html` from within _/sphinx_. **Note: the Makefile (-> make.bat) has not been adapted/tested for Windows**

## 2. Documentation guideline
The documentation is written inside the docstrings. 
The style fo the docstring the follows ReStructuredText syntax which is the default 
for Sphinx.
Docstring are writen in an imperative style for instance:
```"""Do this."""``` instead of ```"""Does this."""``` 

A onliner docstring is of the form:
```
"""This is a oneliner docstring."""
```

If the docstring does not fit in one line it should look like:
```
"""Onliner short description.

Optionnal longer description.
That can be on multiple line.

:param param1: description of param1
...
:return: the return value
"""
```

Modules and classes must have a docstring. 
Methods and attributes which are public must have a docstring but methods and 
attributes which are private do not need a docstring.





 
How to run the Project
---
There two files that are used to run the model:
- server.py
- cli.py

**cli.py** - to run, pass this code from the cmd: python cli.py --input cli

## **Changing Lookup Table**
To change keywords in which the model looks for, go to config and then change the contents of settings.yaml

## **Steps on Setting up the Project**
Simply install this following modules:
- pip3 install pandas
- pip3 install numpy
- pip3 install -u spacy

Then download the corpus for spacy: python -m spacy download en_core_web_sm

**...Or just run the pip3 install -r requirements.txt**

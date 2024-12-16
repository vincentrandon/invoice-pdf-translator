# PDF Invoice Translator

Had to come up with a tool to translate invoices from French to English.

A Python-based tool for processing and manipulating PDF files with features for text extraction, translation, and PDF generation.

## Features

- PDF text extraction
- PDF manipulation and merging
- PDF generation using ReportLab
- Text translation capabilities
- Type-safe implementation

## Prerequisites

- Python 3.11
- pip package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/vincentrandon/invoice-pdf-translator.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the tool:
```bash
python main.py
```


## Dependencies

- pdfplumber (v0.7.4) - For PDF text extraction
- PyPDF2 (v3.0.1) - For PDF manipulation
- reportlab (v3.6.12) - For PDF generation
- deep-translator (v1.9.1) - For text translation
- typing (v3.7.4.3) - For type hints


## Usage

- Place your PDF files in the `invoices` directory.
- Run the tool, and it will process the PDF files and generate translated versions in the `translated_invoices` directory.


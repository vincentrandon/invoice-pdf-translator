import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
from deep_translator import GoogleTranslator
from typing import Dict, List, Tuple
import os

class InvoiceTranslator:
    def __init__(self):
        self.business_terms = {
            "facture": "invoice",
            "montant": "amount",
            "total hors taxes": "subtotal",
            "tva": "vat",
            "total ttc": "total including tax",
            "date d'échéance": "due date",
            "numéro de facture": "invoice number",
            "référence client": "customer reference",
            "conditions de paiement": "payment terms",
            "paiement à réception": "payment upon receipt",
            "à payer avant le": "to be paid before",
            "siège social": "registered office",
            "numéro de siret": "company registration number",
            "numéro de tva": "vat number",
            "description": "description",
            "quantité": "quantity",
            "prix unitaire": "unit price",
            "remise": "discount",
            "sous-total": "subtotal",
            "total à payer": "total payable",
            "date de facturation": "invoice date",
            "date d'émission": "issue date",
            "bon pour accord": "approved",
            "acompte": "deposit",
            "en votre aimable règlement": "awaiting your payment",
            "coordonnées bancaires": "bank details",
            "iban": "iban",
            "bic": "bic",
            "libellé": "Label",
            "unité": "Unit",
            "quantité": "Quantity",
            "prix u. ht": "Unit Price",
            "prix u.": "Unit Price",
            "tva": "VAT",
            "total ht": "Total excl. tax",
            "total ttc": "Total incl. tax",
            "émise le": "Issued on",
            "échéance de paiement": "Payment deadline",
            "30 jours à compter de la réalisation de la": "30 days from the completion of the",
            "prestation ou de la réception de la": "provision or receipt of the",
            "marchandise": "merchandise",
            "€": "€",
            "eur": "EUR"
        }
        
        self.translator = GoogleTranslator(source='fr', target='en')
        
        self.fallback_fonts = {
            'Helvetica': 'helv',
            'Times-Roman': 'tiro',
            'Courier': 'cour',
        }
    
    def get_font_name(self, original_font: str) -> str:
        """Map original font to available system font"""
        return self.fallback_fonts.get(original_font, 'helv')

    def normalize_color(self, color) -> Tuple[float, float, float]:
        """Convert color to RGB tuple in range 0-1"""
        try:
            if color is None:
                return (0, 0, 0)
            
            if isinstance(color, (int, float)):
                val = max(0, min(1, float(color)))
                return (val, val, val)
            
            if isinstance(color, (tuple, list)):
                if len(color) == 1:  # Grayscale
                    val = max(0, min(1, float(color[0])))
                    return (val, val, val)
                elif len(color) == 3:  # RGB
                    return tuple(max(0, min(1, float(c))) for c in color)
                elif len(color) == 4:  # CMYK to RGB
                    c, m, y, k = [max(0, min(1, float(x))) for x in color]
                    r = 1 - min(1, c * (1 - k) + k)
                    g = 1 - min(1, m * (1 - k) + k)
                    b = 1 - min(1, y * (1 - k) + k)
                    return (r, g, b)
            
            return (0, 0, 0)  # Default to black
        except Exception as e:
            print(f"Color normalization error: {str(e)} for color value: {color}")
            return (0, 0, 0)  # Default to black

    def extract_pdf_structure(self, pdf_path: str) -> List[Dict]:
        """Extract complete PDF structure including formatting"""
        doc = fitz.open(pdf_path)
        elements = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            raw_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
            
            for block in raw_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            try:
                                text = span.get("text", "").strip()
                                if not text:  # Skip empty spans
                                    continue
                                
                                # Clean up Unicode spaces and dots
                                text = text.replace('\xa0', ' ')  # Replace non-breaking space
                                text = text.replace('\u202f', ' ')  # Replace narrow non-breaking space
                                text = text.replace('•', '_DOT_')  # Replace bullet point
                                
                                elements.append({
                                    'text': text,
                                    'font': span.get('font', 'helv'),
                                    'size': span.get('size', 11),
                                    'color': span.get('color', (0, 0, 0)),
                                    'bbox': span.get('bbox', (0, 0, 0, 0)),
                                    'page_number': page_num + 1
                                })
                                
                            except Exception as e:
                                print(f"Warning: Could not process span: {str(e)}, span data: {span}")
                                continue
        
        doc.close()
        return elements

    def translate_text(self, text: str) -> str:
        """Translate text with business term handling."""
        if not text or not isinstance(text, str):
            return ""

        # Clean up any remaining quotes and spaces
        text = text.strip("'\"").strip()
        
        # Handle our dot marker
        if '_DOT_' in text:
            # Split into words to handle each number separately
            words = text.split()
            result = []
            for word in words:
                if '_DOT_' in word:
                    # Handle number formatting
                    number_part = word.replace('_DOT_', '')
                    try:
                        if ',' in number_part:
                            num = float(number_part.replace(',', '.'))
                        else:
                            num = float(number_part)
                        formatted = "{:,.2f}".format(num).replace(',', ' ').replace('.', ',')
                        result.append(f"{formatted} €")
                    except ValueError:
                        result.append(word.replace('_DOT_', '€'))
                else:
                    result.append(word)
            
            return ' '.join(result)

        # Check for French text that needs translation
        text_lower = text.lower().strip()
        if text_lower in self.business_terms:
            translated = self.business_terms[text_lower]
            if text.isupper():
                return translated.upper()
            elif text[0].isupper():
                return translated.capitalize()
            return translated
        
        # Handle numbers with euro symbols
        if '€' in text:
            return text
        
        try:
            if not any(english in text_lower for english in self.business_terms.values()):
                return self.translator.translate(text)
            return text
        except:
            return text

    def create_translated_pdf(self, input_pdf: str, output_pdf: str, elements: List[Dict]):
        """Create PDF maintaining exact formatting"""
        doc = fitz.open(input_pdf)
        new_doc = fitz.open()
        
        # Initialize built-in fonts
        font_buffer = {
            'helv': 'Helvetica',
            'helv-b': 'Helvetica-Bold',
            'tiro': 'Times-Roman',
            'cour': 'Courier'
        }
        
        # Track table headers to maintain consistent formatting
        table_headers = set([
            "Label", "Unit", "Quantity", "Unit Price", 
            "VAT", "Total excl. tax", "Total incl. tax"
        ])
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Copy original content
            new_page.show_pdf_page(new_page.rect, doc, page_num)
            
            for elem in [e for e in elements if e['page_number'] == page_num + 1]:
                try:
                    rect = fitz.Rect(elem['bbox'])
                    translated_text = self.translate_text(elem['text'])
                    
                    # Special handling for table headers
                    if translated_text in table_headers:
                        font_size = elem['size'] * 1.0
                        font_name = 'helv-b'
                    else:
                        font_size = elem['size']
                        font_name = elem['font']
                    
                    # Ensure color is properly formatted
                    color = self.normalize_color(elem.get('color', (0, 0, 0)))
                    if not isinstance(color, tuple) or len(color) != 3:
                        color = (0, 0, 0)
                    
                    # Create white rectangle to cover original text
                    new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    # Get system font name
                    system_font = font_buffer.get(font_name, 'Helvetica')
                    
                    # Insert translated text with proper formatting
                    new_page.insert_text(
                        point=rect.tl,
                        text=translated_text,
                        fontsize=font_size,
                        color=color,
                        fontname=system_font
                    )
                except Exception as e:
                    print(f"Warning: Could not process text element: {str(e)}")
                    continue
        
        new_doc.save(output_pdf)
        new_doc.close()
        doc.close()

    def process_invoice(self, input_pdf: str, output_pdf: str):
        try:
            print("Analyzing PDF structure...")
            elements = self.extract_pdf_structure(input_pdf)
            
            print("Creating translated PDF...")
            self.create_translated_pdf(input_pdf, output_pdf, elements)
            
            print(f"Translation completed. Output saved to: {output_pdf}")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def main():
    translator = InvoiceTranslator()
    
    # Update this path to your input PDF
    input_pdf = "invoices/your_invoice.pdf"
    output_pdf = "translated_invoice.pdf"
    
    translator.process_invoice(input_pdf, output_pdf)

if __name__ == "__main__":
    main()

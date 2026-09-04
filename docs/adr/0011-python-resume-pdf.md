# Python generates Resume PDFs from a stored template

Resume PDFs are rendered in the FastAPI process with ReportLab, following a stored ResumeTemplate (A4 single-column, dates on the right). We rejected HTML-to-PDF (WeasyPrint / wkhtmltopdf) because those pull in system browsers or GTK and drift from the extracted layout contract. The public `/resume` page is still the site’s liquid-glass UI; the PDF is the ATS-facing artifact.

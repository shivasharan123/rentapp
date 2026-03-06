import markdown
import base64
import os

# Read updated markdown
with open('Rent_App_Proposal.md', 'r') as f:
    md_content = f.read()

# Read image
try:
    with open('rent-app-flowchart.png', 'rb') as f:
        img_data = f.read()
        img_b64 = base64.b64encode(img_data).decode('utf-8')
except FileNotFoundError:
    img_b64 = ""  # Should not happen

# Inject image into first section (Title/Exec Summary)
sections = md_content.split('---')
sections = [s for s in sections if s.strip()]

if sections:
    # Scale image to fit A4 width better (max-width: 90%)
    sections[0] += f'\n\n<div style="text-align: center;"><img src="data:image/png;base64,{img_b64}" style="max-width:90%; max-height:120mm; display:inline-block; margin:20px auto; border:1px solid #ddd; border-radius:8px;"></div>\n\n'

html_slides = []
for section in sections:
    if not section.strip(): continue
    html = markdown.markdown(section.strip())
    html_slides.append(f'<div class="slide">\n{html}\n</div>')

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Rent App Proposal - A4 Portrait</title>
<style>
/* Default Screen Style (Clean Document Look) */
body {{ 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    background: #f0f2f5; 
    margin: 0; 
    padding: 20px; 
    color: #333;
}}

.slide {{ 
    background: white; 
    padding: 60px; 
    margin: 40px auto; 
    max-width: 210mm; /* Simulate A4 width on screen */
    min-height: 297mm; /* Simulate A4 height on screen */
    box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
    display: flex; 
    flex-direction: column; 
    justify-content: flex-start;
    box-sizing: border-box;
}}

/* Typography */
h1 {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 15px; margin-bottom: 30px; font-size: 24pt; }}
h2 {{ color: #5f6368; font-weight: 400; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-top: 0; font-size: 18pt; }}
h3 {{ color: #202124; margin-top: 0; font-size: 16pt; margin-bottom: 20px; }}
h4 {{ color: #1a73e8; margin-top: 25px; margin-bottom: 10px; font-size: 14pt; }}
p {{ margin-bottom: 15px; font-size: 12pt; }}
ul {{ line-height: 1.6; padding-left: 25px; margin-bottom: 20px; }}
li {{ margin-bottom: 8px; font-size: 12pt; }}

/* Tables */
table {{ width: 100%; border-collapse: collapse; margin: 25px 0; font-size: 11pt; }}
th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
th {{ background: #f8f9fa; color: #202124; font-weight: 600; }}

/* Print Specifics (A4 Portrait) */
@media print {{
    @page {{ size: A4 portrait; margin: 0; }}
    body {{ background: white; padding: 0; margin: 0; -webkit-print-color-adjust: exact; }}
    
    .slide {{ 
        box-shadow: none; 
        margin: 0; 
        border: none; 
        width: 210mm;  /* Exact A4 width */
        height: 297mm; /* Exact A4 height */
        padding: 25mm; /* Standard document margins */
        page-break-after: always;
        overflow: hidden; /* Prevent spillover to next page */
    }}
    
    /* Ensure only one slide per page */
    .slide:last-child {{ page-break-after: auto; }}
}}
</style>
</head>
<body>
{''.join(html_slides)}
</body>
</html>"""

with open('Rent_App_Presentation_A4.html', 'w') as f:
    f.write(full_html)
print("A4 Portrait Presentation generated successfully.")

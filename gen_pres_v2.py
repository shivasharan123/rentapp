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

# Remove truly empty sections (whitespace only)
sections = [s for s in sections if s.strip()]

# Add image to the first section (Title)
if sections:
    sections[0] += f'\n\n<img src="data:image/png;base64,{img_b64}" style="max-width:100%; height:auto; display:block; margin:20px auto; border:1px solid #ddd; border-radius:8px;">\n\n'

html_slides = []
for section in sections:
    if not section.strip(): continue
    html = markdown.markdown(section.strip())
    # Add page-break-inside avoid to prevent weird breaks
    html_slides.append(f'<div class="slide">\n{html}\n</div>')

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Rent App Proposal - V2</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
.slide {{ 
    background: white; 
    padding: 60px; 
    margin: 40px auto; 
    max-width: 900px; 
    min-height: 500px; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
    border-radius: 8px; 
    display: flex; 
    flex-direction: column; 
    justify-content: center;
    page-break-inside: avoid; /* Prevent breaking inside a slide */
}}
h1 {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 10px; }}
h2 {{ color: #5f6368; font-weight: 400; }}
h3 {{ color: #202124; margin-top: 0; }}
h4 {{ color: #1a73e8; margin-top: 20px; }}
ul {{ line-height: 1.6; padding-left: 20px; }}
li {{ margin-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
th {{ background: #f8f9fa; color: #202124; }}
code {{ background: #f1f3f4; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
@media print {{
    body {{ background: white; padding: 0; margin: 0; }}
    .slide {{ 
        box-shadow: none; 
        margin: 0; 
        border: none; 
        min-height: 100vh; /* Force full page height for print */
        page-break-after: always; /* Force new page after each slide */
        padding: 40px; 
        width: 100%;
        max-width: 100%;
    }}
    /* Remove page break after the last slide */
    .slide:last-child {{ page-break-after: auto; }}
}}
</style>
</head>
<body>
{''.join(html_slides)}
</body>
</html>"""

with open('Rent_App_Presentation_v2.html', 'w') as f:
    f.write(full_html)
print("Presentation V2 generated successfully.")

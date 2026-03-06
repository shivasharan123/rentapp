import markdown
import base64
import os

# Read markdown
with open('Rent_App_Proposal.md', 'r') as f:
    md_content = f.read()

# Read image
with open('rent-app-flowchart.png', 'rb') as f:
    img_data = f.read()
    img_b64 = base64.b64encode(img_data).decode('utf-8')

# Inject image into first section (Title/Exec Summary)
# The markdown has "---" separators.
sections = md_content.split('---')

# Insert image after title block (first section)
# Usually title is first. I'll append it to the end of the first section.
if sections:
    sections[0] += f'\n\n<img src="data:image/png;base64,{img_b64}" style="max-width:100%; height:auto; display:block; margin:20px auto; border:1px solid #ddd; border-radius:8px;">\n\n'

html_slides = []
for section in sections:
    if not section.strip(): continue
    html = markdown.markdown(section.strip())
    html_slides.append(f'<div class="slide">\n{html}\n</div>')

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
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
}}
h1 {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 10px; }}
h2 {{ color: #5f6368; font-weight: 400; }}
h3 {{ color: #202124; margin-top: 0; }}
ul {{ line-height: 1.8; }}
li {{ margin-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
th {{ background: #f8f9fa; color: #202124; }}
code {{ background: #f1f3f4; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
@media print {{
    body {{ background: white; padding: 0; }}
    .slide {{ box-shadow: none; margin: 0; border: none; min-height: 100vh; page-break-after: always; padding: 40px; }}
}}
</style>
</head>
<body>
{''.join(html_slides)}
</body>
</html>"""

with open('Rent_App_Presentation.html', 'w') as f:
    f.write(full_html)
print("Presentation generated successfully.")

from flask import Flask, render_template, request, jsonify
from email.message import EmailMessage
from datetime import datetime
import os
import smtplib
import ssl

app = Flask(__name__)

# ------------- CONFIG -------------

# Sender email (account used to send emails)
EMAIL_FROM = os.environ.get("SMTP_FROM", "change_me@your-domain.com")
# Recipient (you)
EMAIL_TO = "carlos.tamez@ext.us.panasonic.com"

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.your-domain.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "your_smtp_username")
SMTP_PASS = os.environ.get("SMTP_PASS", "your_smtp_password")

COUNTER_FILE = "project_counter.txt"
INTAKE_DIR = "intakes"

os.makedirs(INTAKE_DIR, exist_ok=True)


# ------------- UTILITIES -------------

def get_next_project_id():
    """
    Generate a numeric project ID (6 digits) stored in a simple counter file.
    Example: 000001, 000002, ...
    """
    if not os.path.exists(COUNTER_FILE):
        last = 0
    else:
        with open(COUNTER_FILE, "r") as f:
            try:
                last = int(f.read().strip())
            except ValueError:
                last = 0

    new = last + 1

    with open(COUNTER_FILE, "w") as f:
        f.write(str(new))

    return f"{new:06d}"


def build_text_file_content(data: dict) -> str:
    """Create a text block with all answers in a readable format."""
    lines = []
    lines.append(f"Project ID: {data.get('project_id','')}")
    lines.append(f"Company Name: {data.get('company_name','')}")
    lines.append(f"Contact Name: {data.get('contact_name','')}")
    lines.append(f"Email: {data.get('email','')}")
    lines.append(f"Phone: {data.get('phone','')}")
    lines.append(f"City / State / Country: {data.get('location','')}")
    lines.append("")
    lines.append(f"Estimated Order Date: {data.get('estimated_order_date','')}")
    lines.append(f"Estimated Start of Production: {data.get('estimated_start_of_production','')}")
    lines.append("")
    lines.append(f"PCB Processing: {data.get('pcb_processing','')}")
    lines.append("")
    lines.append(f"Max PCB Size Category: {data.get('max_pcb_size_category','')}")
    lines.append(f"Max PCB Width Tier: {data.get('max_pcb_width_tier','')}")
    lines.append(f"Max PCB Length Tier: {data.get('max_pcb_length_tier','')}")
    lines.append("")
    lines.append(f"Min PCB Size Category: {data.get('min_pcb_size_category','')}")
    lines.append("")
    lines.append(f"Component Package Types: {data.get('component_package_types','')}")
    lines.append("")
    lines.append(f"Demanding Operating Conditions?: {data.get('demanding_conditions','')}")
    lines.append(f"OEM Specified Nitrogen?: {data.get('oem_nitrogen','')}")
    lines.append("")
    lines.append(f"Files Provided: {data.get('files_provided','No')}")
    lines.append(f"File Links: {data.get('file_links','')}")
    lines.append("")
    lines.append("---- Preliminary Summary ----")
    lines.append(f"PCB Process: {data.get('pcb_processing','')}")
    lines.append(f"Max PCB Size Category: {data.get('max_pcb_size_category','')}")
    lines.append(f"Width Tier: {data.get('max_pcb_width_tier','')}")
    lines.append(f"Length Tier: {data.get('max_pcb_length_tier','')}")
    lines.append(f"Min PCB Size: {data.get('min_pcb_size_category','')}")
    lines.append(f"Component Types: {data.get('component_package_types','')}")
    lines.append(f"Operating Conditions: {data.get('demanding_conditions','')}")
    lines.append(f"OEM Requirement (Nitrogen): {data.get('oem_nitrogen','')}")
    lines.append(f"Files Provided: {data.get('files_provided','No')}")
    return "\n".join(lines)


def send_email_with_attachment(subject: str, body: str, filename: str, file_content: str):
    """Send email with the .txt as attachment."""
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        file_content.encode("utf-8"),
        maintype="text",
        subtype="plain",
        filename=filename
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ------------- ROUTES -------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/new_project", methods=["GET"])
def new_project():
    project_id = get_next_project_id()
    return jsonify({"project_id": project_id})


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True)

    # Build text content
    text_content = build_text_file_content(data)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    project_id = data.get("project_id", "unknown")
    filename = f"tso_intake_{project_id}_{timestamp}.txt"
    filepath = os.path.join(INTAKE_DIR, filename)

    # Save to local .txt
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text_content)

    # Try to send email, but do not fail if SMTP is not configured correctly yet
    subject = f"TSO Intake - Project {project_id}"
    body = f"Please find attached the intake file for Project ID {project_id}."

    try:
        send_email_with_attachment(subject, body, filename, text_content)
        email_status = "emailed"
    except Exception as e:
        print(f"Email error: {e}")
        email_status = "saved_only"

    return jsonify({"status": "ok", "message": f"Intake {email_status}."})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

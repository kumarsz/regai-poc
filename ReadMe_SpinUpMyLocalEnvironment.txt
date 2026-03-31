================================================================================
REGAI POC — CLOUD9 ENVIRONMENT SETUP GUIDE
================================================================================
Author  : Kumar Saminathan
Project : RegAI POC — Agentic AI for Regulatory Reporting--
GitHub  : https://github.com/kumarsz/regai-poc
================================================================================


STEP 1 — OPEN CLOUD9 TERMINAL
--------------------------------------------------------------------------------
When Cloud9 opens, you will be at:
  /home/ec2-user/environment

Open a terminal (bottom panel or Alt+T) and confirm:
  pwd
  Expected: /home/ec2-user/environment


STEP 2 — CLONE THE REPOSITORY
--------------------------------------------------------------------------------
  cd /home/ec2-user/environment/applications
  git clone https://github.com/kumarsz/regai-poc.git
  cd regai-poc

If the folder already exists (re-using old instance), just pull latest:
  cd /home/ec2-user/environment/applications/regai-poc
  git pull


STEP 3 — INSTALL PYTHON DEPENDENCIES
--------------------------------------------------------------------------------
  pip install -r requirements.txt

If pip is not found, use pip3:
  pip3 install -r requirements.txt


STEP 4 — CONFIGURE AWS CREDENTIALS
--------------------------------------------------------------------------------
Check if credentials are already configured (IAM role attached to instance):
  aws sts get-caller-identity

Expected output: your AWS account ID and role name.
If this works — skip to Step 5. No manual configuration needed.

If it fails, configure manually:
  aws configure
  AWS Access Key ID     : <your access key>
  AWS Secret Access Key : <your secret key>
  Default region name   : us-east-1
  Default output format : json


STEP 5 — RECREATE THE RADAR DATABASE
--------------------------------------------------------------------------------
The radar.db file is not stored in GitHub (intentionally excluded).
Recreate it from the setup script:

  python3 /home/ec2-user/environment/applications/regai-poc/radar_db_setup.py

Expected output:
  RADAR DB created at: /home/ec2-user/environment/applications/regai-poc/radar.db
  Tables created and populated:
    regulators          — 6 rows
    regulations         — 7 rows
    reports             — 9 rows
    systems             — 6 rows
    report_system_map   — 9 rows
    system_capabilities — 19 rows
  RADAR DB ready.


STEP 6 — UPDATE CONFIG WITH KB IDs
--------------------------------------------------------------------------------
Open config.txt and fill in your Bedrock Knowledge Base IDs:
  nano /home/ec2-user/environment/applications/regai-poc/config.txt

Values to fill in:
  KB_ID_RCI = <your RCI Knowledge Base ID from AWS Bedrock>
  KB_ID_SK  = <your SK Knowledge Base ID from AWS Bedrock>

These IDs are found in:
  AWS Console → Bedrock → Knowledge Bases → click each KB → copy the ID


STEP 7 — UPDATE KB ID IN CHAT APP
--------------------------------------------------------------------------------
  nano /home/ec2-user/environment/applications/regai-poc/chat_app.py

Find line:
  KB_ID = "XXXXXXXX"

Replace with your actual KB ID from config.txt.


STEP 8 — START THE RADAR MCP SERVER
--------------------------------------------------------------------------------
Run in background so terminal remains available:

  python3 /home/ec2-user/environment/applications/regai-poc/radar_mcp_server.py &

Confirm it is running:
  ps aux | grep radar_mcp_server

To stop it later:
  pkill -f radar_mcp_server.py


STEP 9 — START THE STREAMLIT APP
--------------------------------------------------------------------------------
  streamlit run /home/ec2-user/environment/applications/regai-poc/chat_app.py \
    --server.port 8080 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false

Expected output:
  You can now view your Streamlit app in your browser.
  URL: http://0.0.0.0:8080


STEP 10 — ACCESS THE APP IN BROWSER
--------------------------------------------------------------------------------
Get your EC2 public IP:
  curl https://checkip.amazonaws.com

Open in your Mac browser:
  http://<your-ec2-public-ip>:8080

If browser cannot connect — check Security Group inbound rules:
  AWS Console → EC2 → your instance → Security tab → Security Group
  Edit inbound rules → Add rule:
    Type     : Custom TCP
    Port     : 8080
    Source   : My IP

Note: Public IP changes on every restart unless you assign an Elastic IP.
      Update the Security Group inbound rule with the new IP each time.


================================================================================
QUICK REFERENCE — DAILY COMMANDS
================================================================================

Start MCP server:
  python3 ~/environment/applications/regai-poc/radar_mcp_server.py &

Start Streamlit:
  streamlit run ~/environment/applications/regai-poc/chat_app.py \
    --server.port 8080 --server.address 0.0.0.0 \
    --server.enableCORS false --server.enableXsrfProtection false

Get public IP:
  curl https://checkip.amazonaws.com

Push code to GitHub:
  cd ~/environment/applications/regai-poc
  git add .
  git commit -m "describe your change"
  git push

Pull latest from GitHub:
  cd ~/environment/applications/regai-poc
  git pull


================================================================================
FILE STRUCTURE
================================================================================

regai-poc/
  chat_app.py                         Streamlit chat interface (POC 2)
  radar_db_setup.py                   Creates and seeds the RADAR SQLite DB
  radar_mcp_server.py                 MCP server exposing RADAR DB as tools
  radar.db                            SQLite DB — NOT in GitHub, regenerate via setup script
  requirements.txt                    Python dependencies
  config.txt                          KB IDs and configuration values
  startup.sh                          One-command startup script
  .gitignore                          Excludes DB, cache, credentials from GitHub
  ReadMe_SpinUpMyLocalEnvironment.txt This file


================================================================================
KNOWLEDGE BASES (AWS BEDROCK)
================================================================================

@RCI KB — Regulatory Circular Information
  Purpose : Historical regulation documents for context retrieval
  Contents: Prior circulars, Basel documents, regulatory guidance

@SK KB — System Knowledge
  Purpose : System capability documents for impact analysis
  Contents: GRACE specs, architecture docs, prior impact analyses

Both KBs are in AWS Bedrock → Knowledge Bases.
IDs are stored in config.txt.


================================================================================
TROUBLESHOOTING
================================================================================

Problem : streamlit command not found
Fix     : pip install streamlit

Problem : boto3 Python 3.9 deprecation warning
Fix     : Warning only — does not affect functionality. Upgrade Python when convenient.

Problem : KB query returns ValidationException on model ID
Fix     : Use model ID with us. prefix: us.anthropic.claude-3-5-haiku-20241022-v1:0

Problem : Browser cannot reach http://<ip>:8080
Fix     : Check Security Group inbound rule has port 8080 open for your IP

Problem : radar.db not found
Fix     : Run python3 radar_db_setup.py to recreate it

Problem : git push asks for password
Fix     : Use GitHub Personal Access Token (not your GitHub password)
          Generate at: GitHub → Settings → Developer settings → Personal access tokens


================================================================================
END OF DOCUMENT
================================================================================
# ##Install required python version and other libraries.

##1.
winget install Python.Python.3.10

##2.
Create a virtual Env :

   python3.12 -m venv .venv312
   .venv312\Scripts\activate


##3.run to install the dependency libraries.

python.exe -m pip install -r c:/Users/ismai/GIT/kokoro-80.py/requirements.txt

Stopping any running Python processes, then restarting the app with the fix:(optional)
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*\.venv\*"} | Stop-Process -Force

Waiting a few seconds for the model to load, then checking if the server is running:

Start-Sleep -Seconds 5; netstat -ano | Select-String ":5001"

cd kokoro-80.py; ..\..venv\Scripts\python.exe kokoro-80.py

<img width="934" height="659" alt="image" src="https://github.com/user-attachments/assets/56bb3a39-b949-4715-b63f-cab3b49b6ed8" />





apt update
apt install -y python3.12-venv
python3 -m venv .venv
. .venv/bin/activate
pip3 install -r requirements.txt
pip3 install -r backend/database_handler/migration/requirements.txt
[ -f .env ] || cp .env.example .env
mkdir -p frontend/src/assets/examples
cp -r examples/* frontend/src/assets/examples/
npm --prefix frontend install
npm --prefix frontend run build
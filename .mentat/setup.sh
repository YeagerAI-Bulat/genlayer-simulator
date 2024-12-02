# Install python dependencies
pip3 install -r requirements.txt
pip3 install -r backend/database_handler/migration/requirements.txt

# Install frontend dependencies and build
cd frontend && npm install && cd ..

# Copy environment file if it doesn't exist
[ -f .env ] || cp .env.example .env
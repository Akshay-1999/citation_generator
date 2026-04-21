### read logs
journalctl -u fastapi -f

### stop the server
bash
sudo systemctl stop fastapi

### deploy
bash
./deploy.sh

### start the server
bash
sudo systemctl start fastapi

### read Postgres Tables
bash
psql -U postgres -d ragdb -c "\dt"

### Check if PostgreSQL is installed
bash
psql --version

### Start and enable PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

### Check status
sudo systemctl status postgresql

### Switch to postgres user
sudo -i -u postgres

### Open PostgreSQL CLI
psql

### switch to ragdb
\c ragdb

### read Postgres Tables
select message_id , file_context_name , confidence_level , citations   from  chathistory.messages

### exit postgres
\q

### switch to ubuntu user
exit

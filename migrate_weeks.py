import sqlite3
from datetime import datetime, timedelta

def update_weeks():
    conn = sqlite3.connect('garment_data.sqlite')
    cursor = conn.cursor()
    rows = cursor.execute('SELECT id, tod FROM orders').fetchall()
    updated_count = 0
    
    for rid, tod in rows:
        if not tod: continue
        dt = None
        for fmt in ['%d-%b-%y', '%d-%b-%Y', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(str(tod), fmt)
                break
            except:
                pass
        
        if dt:
            monday = dt - timedelta(days=dt.weekday())
            week_str = f"Week-{dt.isocalendar()[1]:02d} [{monday.strftime('%d-%b-%y')}]"
            cursor.execute('UPDATE orders SET week=? WHERE id=?', (week_str, rid))
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully updated {updated_count} records with new week format.")

if __name__ == "__main__":
    update_weeks()

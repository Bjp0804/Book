from flask import Flask, render_template, request, jsonify, send_file
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import locale

app = Flask(__name__)
app.title = "Book - Registro de Actividades"

def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        sslmode='require'
    )

# Registrar fuentes Montserrat
try:
    fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    pdfmetrics.registerFont(TTFont('Montserrat', os.path.join(fonts_dir, 'Montserrat-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('Montserrat-Bold', os.path.join(fonts_dir, 'Montserrat-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('Montserrat-Italic', os.path.join(fonts_dir, 'Montserrat-Italic.ttf')))

    # Registrar familia de fuentes
    pdfmetrics.registerFontFamily(
        'Montserrat',
        normal='Montserrat',
        bold='Montserrat-Bold',
        italic='Montserrat-Italic'
    )
except Exception as e:
    print(f"Error loading fonts: {e}")

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    description TEXT,
                    location TEXT
                )
            ''')
            conn.commit()

def convert_to_12h(time_str):
    """Convierte hora de formato 24h a 12h con AM/PM"""
    try:
        hour = int(time_str.split(':')[0])
        minute = time_str.split(':')[1]
        period = 'AM' if hour < 12 else 'PM'
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        return f"{hour:02d}:{minute} {period}"
    except:
        return time_str

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/activities')
def activities():
    selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, start_time, end_time, description, location 
                FROM activities 
                WHERE date = %s 
                ORDER BY start_time::time ASC
            ''', (selected_date,))
            activities = cur.fetchall()
    
    return render_template('activities.html', 
                         activities=activities,
                         selected_date=selected_date)

# Diccionarios para traducción de fechas
months_es = {
    'January': 'enero',
    'February': 'febrero',
    'March': 'marzo',
    'April': 'abril',
    'May': 'mayo',
    'June': 'junio',
    'July': 'julio',
    'August': 'agosto',
    'September': 'septiembre',
    'October': 'octubre',
    'November': 'noviembre',
    'December': 'diciembre'
}

days_es = {
    'Monday': 'lunes',
    'Tuesday': 'martes',
    'Wednesday': 'miércoles',
    'Thursday': 'jueves',
    'Friday': 'viernes',
    'Saturday': 'sábado',
    'Sunday': 'domingo'
}

@app.route('/download_report')
def download_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    single_date = request.args.get('date')

    if start_date and end_date:
        # Lógica para rango de fechas
        date_range = [start_date, end_date]
    elif single_date:
        # Lógica para fecha única
        date_range = [single_date, single_date]
    else:
        # Si no se proporciona ninguna fecha, usar la fecha actual
        today = datetime.now().strftime("%Y-%m-%d")
        date_range = [today, today]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT date, location, start_time, end_time, description 
                FROM activities 
                WHERE date BETWEEN %s AND %s 
                ORDER BY date::date ASC, start_time::time ASC
            ''', date_range)
            
            activities_by_date = {}
            for row in cur.fetchall():
                date = row[0]
                if date not in activities_by_date:
                    activities_by_date[date] = []
                activities_by_date[date].append({
                    'start_time': row[2],
                    'end_time': row[3],
                    'description': row[4],
                    'location': row[1]
                })

    doc = SimpleDocTemplate(
        "reporte_actividades.pdf",
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='MainTitle',
        fontName='Montserrat-Bold',
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    ))
    
    styles.add(ParagraphStyle(
        name='DateStyle',
        fontName='Montserrat-Italic',
        fontSize=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#34495e'),
        spaceBefore=10,
        spaceAfter=30
    ))

    all_elements = []
    
    for date in sorted(activities_by_date.keys()):
        elements = []
        
        elements.append(Paragraph("Registro de Actividades", styles['MainTitle']))
        
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_text = date_obj.strftime('%A %d de %B del %Y')
        
        for en, es in days_es.items():
            date_text = date_text.replace(en, es)
        for en, es in months_es.items():
            date_text = date_text.replace(en, es)
        
        elements.append(Paragraph(date_text.capitalize(), styles['DateStyle']))
        
        table_data = [['Hora Inicio', 'Hora Fin', 'Descripción', 'Lugar']]
        
        for activity in activities_by_date[date]:
            table_data.append([
                convert_to_12h(activity['start_time']),
                convert_to_12h(activity['end_time']),
                activity['description'],
                activity['location']
            ])
        
        if len(table_data) > 1:
            available_width = doc.width
            
            def get_max_width(col_index):
                return max(len(str(row[col_index])) for row in table_data) * 7
            
            time_width = max(get_max_width(0), get_max_width(1))
            location_width = get_max_width(3)
            description_width = available_width - (time_width * 2) - location_width - 40
            
            time_width = max(time_width, 90)
            location_width = max(location_width, 100)
            
            table = Table(table_data, colWidths=[time_width, time_width, description_width, location_width])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Montserrat-Bold'),
                ('FONT', (0, 1), (-1, -1), 'Montserrat'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 12),
                ('LEADING', (0, 0), (-1, -1), 12),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))
            elements.append(table)
        else:
            no_activities_style = ParagraphStyle(
                'NoActivities',
                parent=styles['Normal'],
                fontName='Montserrat-Italic',
                fontSize=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#7f8c8d')
            )
            elements.append(Paragraph("No hay actividades registradas para esta fecha", no_activities_style))
        
        elements.append(Spacer(1, 50))
        signature_style = ParagraphStyle(
            'Signature',
            fontName='Montserrat',
            fontSize=12,
            alignment=TA_CENTER,
            spaceBefore=15
        )
        elements.append(Paragraph("_" * 40, signature_style))
        elements.append(Paragraph("Firma del Coordinador", signature_style))
        
        all_elements.extend(elements)
        if date != sorted(activities_by_date.keys())[-1]:
            all_elements.append(PageBreak())
    
    doc.build(all_elements)
    
    if start_date and end_date:
        filename = f'book_actividades_{start_date}_to_{end_date}.pdf'
    else:
        filename = f'book_actividades_{single_date or today}.pdf'
    
    return send_file(
        'reporte_actividades.pdf',
        as_attachment=True,
        download_name=filename
    )
    
@app.route('/add_activity', methods=['POST'])
def add_activity():
    try:
        data = request.get_json()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO activities (date, start_time, end_time, description, location)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (data['date'], data['start_time'], data['end_time'], 
                      data['description'], data['location']))
                conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/edit_activity/<int:id>', methods=['PUT'])
def edit_activity(id):
    try:
        data = request.get_json()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE activities 
                    SET start_time = %s, end_time = %s, description = %s, location = %s
                    WHERE id = %s
                ''', (data['start_time'], data['end_time'], data['description'], 
                      data['location'], id))
                conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/delete_activity/<int:id>', methods=['DELETE'])
def delete_activity(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM activities WHERE id = %s', (id,))
                conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/clear_database', methods=['POST'])
def clear_database():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM activities')
                conn.commit()
        return jsonify({'success': True, 'message': 'Base de datos limpiada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Inicializar la base de datos al arrancar la aplicación
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

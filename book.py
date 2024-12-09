from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import locale

app = Flask(__name__)
app.title = "Book - Registro de Actividades"

# Registrar fuentes Montserrat
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

def init_db():
    conn = sqlite3.connect('activities.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            description TEXT,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

def format_time_12h(time_str):
    """Convierte formato de 24h a 12h con AM/PM"""
    try:
        time_obj = datetime.strptime(time_str, '%H:%M')
        formatted_time = time_obj.strftime('%I:%M %p').upper()
        return formatted_time
    except:
        return time_str

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/activities')
def activities():
    selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT id, start_time, end_time, description, location 
        FROM activities 
        WHERE date = %s 
        ORDER BY start_time::time ASC
    ''', (selected_date,))
    activities = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('activities.html', 
                         activities=activities,
                         selected_date=selected_date)

@app.route('/download_report')
def download_report():
    selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    
    conn = sqlite3.connect('activities.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT location, start_time, end_time, description 
        FROM activities 
        WHERE date = ? 
        ORDER BY time(start_time) ASC
    ''', (selected_date,))
    
    # Crear lista de actividades
    all_activities = []
    for row in cursor.fetchall():
        all_activities.append({
            'start_time': row[1],
            'end_time': row[2],
            'description': row[3],
            'location': row[0]
        })
    
    conn.close()
    
    # Generar PDF
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')

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

    elements = []
    
    # Título y fecha
    elements.append(Paragraph("Registro de Actividades", styles['MainTitle']))
    date_text = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%A %d de %B del %Y')
    elements.append(Paragraph(date_text.capitalize(), styles['DateStyle']))
    
    # Crear tabla
    table_data = [['Hora Inicio', 'Hora Fin', 'Descripción', 'Lugar']]
    
    # Función para convertir hora a formato 12h con AM/PM
    def convert_to_12h(time_str):
        hour = int(time_str.split(':')[0])
        minute = time_str.split(':')[1]
        period = 'AM' if hour < 12 else 'PM'
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        return f"{hour:02d}:{minute} {period}"
    
    # Agregar actividades a la tabla
    for activity in all_activities:
        table_data.append([
            convert_to_12h(activity['start_time']),
            convert_to_12h(activity['end_time']),
            activity['description'],
            activity['location']
        ])
    
    if len(table_data) > 1:
        # Calcular el ancho disponible
        available_width = doc.width
        
        # Función para calcular el ancho máximo del texto
        def get_max_width(col_index):
            return max(len(str(row[col_index])) for row in table_data) * 7
        
        # Calcular anchos mínimos para cada columna
        time_width = max(get_max_width(0), get_max_width(1))
        location_width = get_max_width(3)
        
        # La columna de descripción tomará el espacio restante
        description_width = available_width - (time_width * 2) - location_width - 40
        
        # Asegurar anchos mínimos
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
    
    # Firma
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
    
    # Generar PDF
    doc.build(elements)
    
    return send_file(
        'reporte_actividades.pdf',
        as_attachment=True,
        download_name=f'book_actividades_{selected_date}.pdf'
    )

@app.route('/add_activity', methods=['POST'])
def add_activity():
    try:
        data = request.get_json()
        conn = sqlite3.connect('activities.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activities (date, start_time, end_time, description, location)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['date'], data['start_time'], data['end_time'], 
              data['description'], data['location']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/edit_activity/<int:id>', methods=['PUT'])
def edit_activity(id):
    try:
        data = request.get_json()
        conn = sqlite3.connect('activities.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE activities 
            SET start_time = ?, end_time = ?, description = ?, location = ?
            WHERE id = ?
        ''', (data['start_time'], data['end_time'], data['description'], 
              data['location'], id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/delete_activity/<int:id>', methods=['DELETE'])
def delete_activity(id):
    try:
        conn = sqlite3.connect('activities.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activities WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/clear_database', methods=['POST'])
def clear_database():
    try:
        conn = sqlite3.connect('activities.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM activities')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Base de datos limpiada correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)

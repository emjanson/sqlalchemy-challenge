# Import the dependencies.
from flask import Flask, g, jsonify
import sqlite3
from sqlalchemy import create_engine, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
import datetime as dt
import os
from datetime import datetime

#################################################
# Database Setup
#################################################
    
# Get the absolute path to the directory containing the script
base_dir = os.path.abspath(os.path.dirname(__file__))

# Construct the absolute path to the SQLite database file
database_path = os.path.join(base_dir, 'Resources/hawaii.sqlite')

# Print the absolute path for debugging purposes
print(f"Absolute Path to Database: {database_path}")

# Check if the database file exists
if not os.path.exists(database_path):
    raise FileNotFoundError(f"The database file '{database_path}' does not exist.")

# reflect an existing database into a new model

# Correctly generate the engine to the correct SQLite file

engine = create_engine(f'sqlite:///{database_path}')
Base = automap_base()

# reflect the tables

Base.prepare(autoload_with=engine)

# Save references to each table

measurement = Base.classes.measurement
station = Base.classes.station

# Create our session (link) from Python to the DB

session = Session(engine)

#################################################
# Flask Setup
#################################################

app = Flask(__name__)

#################################################
# Flask Routes
#################################################

# Display the available routes on the landing page
@app.route('/')
def index():
    # Get a list of available routes
    routes = ['/','/api/v1.0/precipitation', '/api/v1.0/stations', '/api/v1.0/tobs', '/api/v1.0/&lt;start&gt;', '/api/v1.0/&lt;start&gt;/&lt;end&gt;']
    
    # Create links for each route
    links = [f'<a href="{route}">{route}</a>' for route in routes]
    
    # Join the links with line breaks for display
    return '<br>'.join(links)

# Precipitation route for the last year
@app.route('/api/v1.0/precipitation')
def precipitation():
    # Calculate the date one year ago from the last date in the database
    last_date = session.query(func.max(measurement.date)).scalar()
    last_date = dt.datetime.strptime(last_date, '%Y-%m-%d')
    one_year_ago = last_date - dt.timedelta(days=365)

    # Query for precipitation data for the last year
    precipitation_data = (
        session.query(measurement.date, measurement.prcp)
        .filter(measurement.date >= one_year_ago)
        .all()
    )

    # Convert the result to a dictionary with date as key and precipitation as value
    precipitation_dict = {date: prcp for date, prcp in precipitation_data}

    return jsonify(precipitation_dict)

# Stations info route
@app.route('/api/v1.0/stations')
def get_stations():
    # Query all stations and return as JSON
    stations = session.query(
        station.station, 
        station.name,
        station.latitude,
        station.longitude,
        station.elevation
    ).all()

    # Convert the result to a list of dictionaries
    stations_list = [
        {
            'station': station,
            'name': name,
            'latitude': latitude,
            'longitude': longitude,
            'elevation': elevation
        } 
        for station, name, latitude, longitude, elevation in stations
    ]
    
    return jsonify(stations_list)

# TOBS for last year at most active station route
@app.route('/api/v1.0/tobs')
def tobs():
    # Query for the most active station
    most_active_station = (
        session.query(measurement.station, func.count(measurement.station))
        .group_by(measurement.station)
        .order_by(func.count(measurement.station).desc())
        .first()
    )

    if most_active_station:
        most_active_station_id = most_active_station[0]

        # Calculate the date one year ago from the last date in the database
        last_date = session.query(func.max(measurement.date)).scalar()
        last_date = dt.datetime.strptime(last_date, '%Y-%m-%d')
        one_year_ago = last_date - dt.timedelta(days=365)

        # Query for temperature observations for the most active station in the last year
        tobs_data = (
            session.query(measurement.date, measurement.tobs)
            .filter(measurement.date >= one_year_ago)
            .filter(measurement.station == most_active_station_id)
            .all()
        )

        # Convert the result to a dictionary with date as key and temperature as value
        tobs_dict = {date: tobs for date, tobs in tobs_data}

        return jsonify({'most_active_station': most_active_station_id, 'tobs_data': tobs_dict})
    else:
        return jsonify({'error': 'No data available'})
    
# Custom dynamic route '/api/v1.0/<start>' for displaying min, max, mean temps from input date to most recent date
@app.route('/api/v1.0/<start>')
def start_route(start):
    try:
        # Replace hyphens with slashes to convert URL-friendly format to 'MM/DD/YYYY'
        start = start.replace('-', '/')

        # Parse the input date with the correct format
        start_date = datetime.strptime(start, '%m/%d/%Y')

        # Query for min, max, and avg temperatures from the given start date to the end of the dataset
        temperature_data = (
            session.query(
                func.min(measurement.tobs).label('min_temp'),
                func.max(measurement.tobs).label('max_temp'),
                func.avg(measurement.tobs).label('avg_temp')
            )
            .filter(measurement.date >= start_date)
            .first()
        )

        if temperature_data:
            return jsonify({
                'start_date': start_date.strftime('%Y-%m-%d'),  # Format as 'YYYY-MM-DD' for response
                'min_temperature': temperature_data.min_temp,
                'max_temperature': temperature_data.max_temp,
                'avg_temperature': temperature_data.avg_temp
            })
        else:
            return jsonify({'error': 'No data available for the given start date'})
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use MM-DD-YYYY.'})
    
# Custom dynamic route '/api/v1.0/<start>/<end>' to return min, max, and mean temp from a specified date range
@app.route('/api/v1.0/<start>/<end>')
def start_end_route(start, end):
    try:
        # Replace hyphens with slashes to convert URL-friendly format to 'MM/DD/YYYY'
        start = start.replace('-', '/')
        end = end.replace('-', '/')

        # Parse the input dates with the correct format
        start_date = datetime.strptime(start, '%m/%d/%Y')
        end_date = datetime.strptime(end, '%m/%d/%Y')

        # Query for TMIN, TAVG, and TMAX temperatures for the specified date range
        temperature_data = (
            session.query(
                func.min(measurement.tobs).label('min_temp'),
                func.avg(measurement.tobs).label('avg_temp'),
                func.max(measurement.tobs).label('max_temp')
            )
            .filter(measurement.date >= start_date)
            .filter(measurement.date <= end_date)
            .first()
        )

        if temperature_data:
            return jsonify({
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'min_temperature': temperature_data.min_temp,
                'avg_temperature': temperature_data.avg_temp,
                'max_temperature': temperature_data.max_temp
            })
        else:
            return jsonify({'error': 'No data available for the specified date range'})
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use MM-DD-YYYY for start and end dates.'})

# Close the session
@app.teardown_appcontext
def shutdown_session(exception=None):
    session.close()

if __name__ == '__main__':
    app.run(debug=True)
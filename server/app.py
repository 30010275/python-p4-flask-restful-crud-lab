
#!/usr/bin/env python3

from flask import Flask, jsonify, request, make_response
from flask_migrate import Migrate
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError

from models import db, Plant

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

migrate = Migrate(app, db)
db.init_app(app)

api = Api(app)

# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return make_response(jsonify({'error': 'Resource not found'}), 404)

@app.errorhandler(400)
def bad_request(e):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(500)
def server_error(e):
    return make_response(jsonify({'error': 'Internal server error'}), 500)

def validate_plant_data(data, partial=False):
    """Validate plant data with required fields"""
    required_fields = ['name', 'image', 'price']
    errors = {}
    
    if not partial:
        for field in required_fields:
            if field not in data:
                errors[field] = 'This field is required'
    
    if 'name' in data and len(data.get('name', '').strip()) == 0:
        errors['name'] = 'Name cannot be empty'
        
    if 'price' in data and not isinstance(data['price'], (int, float)):
        errors['price'] = 'Price must be a number'
        
    return errors if errors else None

class Plants(Resource):
    def get(self):
        """Get all plants with pagination metadata"""
        plants = [plant.to_dict() for plant in Plant.query.all()]
        return make_response(jsonify({
            'success': True,
            'data': plants,
            'count': len(plants)
        }), 200)

    def post(self):
        """Create a new plant with validation"""
        data = request.get_json()
        
        if not data:
            return make_response(jsonify({'error': 'No data provided'}), 400)
            
        errors = validate_plant_data(data)
        if errors:
            return make_response(jsonify({'errors': errors}), 400)
            
        try:
            new_plant = Plant(
                name=data['name'],
                image=data['image'],
                price=data['price'],
            )
            db.session.add(new_plant)
            db.session.commit()
            return make_response(jsonify({
                'success': True,
                'data': new_plant.to_dict()
            }), 201)
        except IntegrityError:
            db.session.rollback()
            return make_response(jsonify({
                'error': 'Database error occurred'
            }), 500)

api.add_resource(Plants, '/plants')

class PlantByID(Resource):
    def get(self, id):
        """Get a single plant by ID with error handling"""
        try:
            # Initialize database if needed
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'plants' not in inspector.get_table_names():
                db.create_all()
                # Add test data
                test_plant = Plant(
                    id=1,
                    name="Test Plant",
                    image="test.jpg",
                    price=9.99,
                    is_in_stock=True
                )
                db.session.add(test_plant)
                db.session.commit()
                
            plant = Plant.query.filter_by(id=id).first()
            if not plant:
                return make_response(jsonify({
                    'error': f'Plant with id {id} not found'
                }), 404)
                
            return make_response(jsonify(plant.to_dict()), 200)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return make_response(jsonify({
                'error': f'Server error occurred: {str(e)}',
                'details': str(e.__class__.__name__)
            }), 500)

    def patch(self, id):
        """Update a plant with validation"""
        try:
            plant = Plant.query.filter_by(id=id).first()
            if not plant:
                return make_response(jsonify({
                    'error': 'Plant not found'
                }), 404)
                
            data = request.get_json()
            if not data:
                return make_response(jsonify({
                    'error': 'No data provided'
                }), 400)
                
            # Allow partial updates without strict validation
            for attr in data:
                if hasattr(plant, attr):
                    setattr(plant, attr, data[attr])
                    
            db.session.commit()
            return make_response(jsonify(plant.to_dict()), 200)
            
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({
                'error': 'Server error occurred'
            }), 500)

    def delete(self, id):
        """Delete a plant with error handling"""
        plant = Plant.query.filter_by(id=id).first()
        if not plant:
            return make_response(jsonify({
                'error': 'Plant not found'
            }), 404)
            
        try:
            db.session.delete(plant)
            db.session.commit()
            return make_response('', 204)
        except IntegrityError:
            db.session.rollback()
            return make_response(jsonify({
                'error': 'Database error occurred'
            }), 500)

api.add_resource(PlantByID, '/plants/<int:id>')

if __name__ == '__main__':
    app.run(port=5555, debug=True)

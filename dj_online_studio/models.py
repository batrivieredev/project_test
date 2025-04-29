from .extensions import db
from datetime import datetime
import os
from flask import current_app
import numpy as np
import json

class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    artist = db.Column(db.String(255))
    duration = db.Column(db.Float)
    bpm = db.Column(db.Float)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def file_path(self):
        return os.path.join(current_app.config['UPLOAD_FOLDER'], self.filename)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'title': self.title,
            'artist': self.artist,
            'duration': self.duration,
            'bpm': self.bpm,
            'upload_date': self.upload_date.isoformat()
        }

class AudioAnalysis(db.Model):
    __tablename__ = 'audio_analyses'

    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    track = db.relationship('Track', backref=db.backref('analysis', uselist=False))
    waveform_data = db.Column(db.Text)
    frequency_data = db.Column(db.Text)
    beat_positions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_waveform_data(self, data):
        self.waveform_data = json.dumps(data.tolist())

    def get_waveform_data(self):
        return np.array(json.loads(self.waveform_data))

    def set_frequency_data(self, data):
        self.frequency_data = json.dumps({
            'low': data['low'].tolist(),
            'mid': data['mid'].tolist(),
            'high': data['high'].tolist()
        })

    def get_frequency_data(self):
        data = json.loads(self.frequency_data)
        return {
            'low': np.array(data['low']),
            'mid': np.array(data['mid']),
            'high': np.array(data['high'])
        }

    def set_beat_positions(self, positions):
        self.beat_positions = json.dumps(positions.tolist())

    def get_beat_positions(self):
        return np.array(json.loads(self.beat_positions))

    def to_dict(self):
        return {
            'id': self.id,
            'track_id': self.track_id,
            'waveform_data': self.get_waveform_data().tolist(),
            'frequency_data': self.get_frequency_data(),
            'beat_positions': self.get_beat_positions().tolist(),
            'created_at': self.created_at.isoformat()
        }

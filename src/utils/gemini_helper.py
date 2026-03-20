import google.generativeai as genai
import os

class GeminiWarden:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def ask(self, query, traffic_data):
        """
        Asks the AI Traffic Warden about the current state.
        """
        if not self.model:
            return "Warden is offline. Please provide a GEMINI_API_KEY."
            
        context = f"""
        You are the AI Traffic Warden for a smart city. 
        Current Data:
        - Road 1 Vehicles: {traffic_data.get('road1_count')}
        - Road 2 Vehicles: {traffic_data.get('road2_count')}
        - Active Signal: {traffic_data.get('road1_signal')} on Road 1, {traffic_data.get('road2_signal')} on Road 2.
        - Emergency Status: {'Active' if traffic_data.get('road1_emergency') or traffic_data.get('road2_emergency') else 'None'}
        - CO2 Saved: {traffic_data.get('total_co2_saved')} kg
        
        Answer the user's query briefly and professionally.
        """
        
        try:
            response = self.model.generate_content(context + "\nUser Query: " + query)
            return response.text
        except Exception as e:
            return f"Error contacting Warden: {e}"

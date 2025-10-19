import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> requestAPI(String query, String selectedCity, List<Map<String, dynamic>> context) async {
      final uri = Uri.parse('http://127.0.0.1:5000/api/query');

      try {
        final res = await http.post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'query': query,
            'city': selectedCity,
            'conversation_context': context.take(3).toList(), // Send last 3 messages for context
            'timestamp': DateTime.now().toIso8601String(),
          }),
        );

        if (res.statusCode == 200) {
          final decodedBody = jsonDecode(res.body) as Map<String, dynamic>;
          final sourcesDynamic = decodedBody['retrieved_sources'] as List<dynamic>?;
          final List<Map<String, dynamic>> sourcesList = sourcesDynamic
                  ?.whereType<Map<String, dynamic>>()
                  .toList() ??
              [];

          return {
            'ai_response': decodedBody['ai_response'] as String? ?? 'Error: No AI response received.',
            'retrieved_sources': sourcesList,
          };
        } else {
          
          return {
            'ai_response': '⚠️ Server Error ${res.statusCode}. Please check connection or try again later.',
            'retrieved_sources': <Map<String, dynamic>>[],
          };
        }
      } catch (e) {
        
        return {
          'ai_response': '⚠️ Network Error. Could not connect to the server. Please check your connection or ensure the server is running.',
          'retrieved_sources': <Map<String, dynamic>>[],
        };
      }
    }

import 'package:flutter/material.dart';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Paralegal Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
        brightness: Brightness.dark,          // keeps the overall palette dark
        seedColor: const Color.fromARGB(255, 34, 55, 82),   // dark navy‑charcoal hex
        ),
      scaffoldBackgroundColor: const Color.fromARGB(255, 217, 217, 217),
      ),
      home: const MyHomePage(title: 'Paralegal Demo Home Page'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;
  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        centerTitle: true,
        title: const Text('Paralegal'),
      ),
      body: const Padding(
        padding: EdgeInsets.all(50.0),
        child: ChatWindow(),
      ),
    );
  }
}


// -------------------- Chat message model --------------------
class ChatMessage {
  final String text;
  final DateTime time;
  final bool fromMe; // true = user, false = server
  ChatMessage({required this.text, required this.time, required this.fromMe});
}

// ------------- Chat window with cooldown (no persistence) -------------
class ChatWindow extends StatefulWidget {
  const ChatWindow({super.key});
  @override
  State<ChatWindow> createState() => _ChatWindowState();
}

class _ChatWindowState extends State<ChatWindow> {
  final _messages = <ChatMessage>[];
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _canSend = true;
  static const _cooldown = Duration(seconds: 5);
  String? _lastMessage; // stores most‑recent user text

  /// Handles the user pressing *Send* or hitting *Enter*.
  /// ------------------------------------------------------
  ///                   Send Function
  /// -----------------------------------------------------
 // ---------------------------------------------------------------------
  Future<void> _send() async {
    // ─── 1.  Cool‑down guard ──────────────────────────────────────────
    // If the timer hasn’t expired, ignore the tap/keypress.
    if (!_canSend) return;

    // ─── 2.  Grab & validate the input ────────────────────────────────
    final text = _input.text.trim(); // remove leading/trailing spaces
    if (text.isEmpty) return;        // don’t send blank messages

    _lastMessage = text;             // store latest message

    // ─── 3.  Add the user message & start cool‑down ──────────────────
    setState(() {
      _messages.add(
        ChatMessage(text: text, time: DateTime.now(), fromMe: true),
      );
      _canSend = false; // disable the send button for 3 seconds
    });

    _input.clear(); // ─── 4.  Clear the TextField for the next message ─

    // ─── 5.  Query the API & append its reply to the chat ────────────────────────
    final reply = await requestAPI(_lastMessage!);
    setState(() {
      _messages.add(
        ChatMessage(text: reply, time: DateTime.now(), fromMe: false),
      );
    });

    // ─── 6.  Re‑enable the send button after the cool‑down ────────────
    Timer(_cooldown, () => setState(() => _canSend = true));

    // ─── 7.  Auto‑scroll to the newest message *after* the frame draws ─
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent + 60, // a small bottom padding
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeOut,
      );
    });
  }

 // ───────────────────────── API helper ─────────────────────────
  /// Send `query` to the Flask API and return the reply text.
Future<String> requestAPI(String query) async {
  final uri = Uri.parse('http://127.0.0.1:5000/chat'); // change for production

  try {
    // POST {"message": query}
    final res = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'message': query}),
    );

    // Success → pull "reply" from JSON
    if (res.statusCode == 200) {
      return (jsonDecode(res.body) as Map<String, dynamic>)['reply'] as String;
    }

    // Non‑200 HTTP code
    return '⚠️ Server ${res.statusCode}: ${res.reasonPhrase}';
  } catch (e) {
    // Network / parsing error
    return '⚠️ Error: $e';
  }
}

  // build the chat window
  // ============================== UI ===============================
   @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            itemCount: _messages.length,
            itemBuilder: (context, i) {
              final m = _messages[i];
              final align = m.fromMe ? Alignment.centerRight : Alignment.centerLeft;
              final bubble = m.fromMe
                  ? Theme.of(context).colorScheme.primaryContainer
                  : Theme.of(context).colorScheme.primaryContainer;
              return Align(
                alignment: align,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: bubble,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    m.text,
                    style: const TextStyle(color: Colors.white),
                  ),
                ),
              );
            },
          ),
        ),
        Row(
          children: [
            Expanded(
              child: TextField(
                style: TextStyle(color: Colors.black),
                controller: _input,
                onSubmitted: (_) => _send(),
                decoration: const InputDecoration(
                  hintText: 'Type a message',
                  hintStyle: TextStyle(color: Colors.black) ,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                  ),
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
              ),
            ),
            IconButton(
              icon: Icon(
                _canSend ? Icons.send : Icons.hourglass_empty,
                color: _canSend ? const Color(0xFF1D2939) : const Color(0xFFC0392B),
              ),
              onPressed: _canSend ? _send : null,
            ),
          ],
        ),
      ],
    );
  }
}
import 'package:flutter/material.dart';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:ui'; // Required for ImageFilter.blur
import 'package:flutter_animate/flutter_animate.dart'; // Import flutter_animate
import 'package:loading_animation_widget/loading_animation_widget.dart'; // Import loading widget


// --- Constants (Keep these the same) ---
Color kBgDark = Colors.blueGrey[900]!;//Color(0xFF1A237E); // Deep Indigo
const Color kBgLight = Color(0xFF3F51B5); // Indigo
const Color kAccentColor = Color(0xFF00BCD4); // Cyan
const Color kUserBubbleColor = Color(0x77FFFFFF); // Semi-transparent white
const Color kAiBubbleColor = Color(0x55000000); // Semi-transparent dark
const Color kTextColor = Colors.white;
const Color kSourceChipColor = Color(0xFFB2EBF2); // Light Cyan
const Color kSourceChipTextColor = Colors.black87;
const Duration kAnimationDuration = Duration(milliseconds: 400);
const Duration kTransitionDuration = Duration(milliseconds: 500); // For view switching

void main() => runApp(const MyApp());

// --- MyApp (Theme setup - largely unchanged) ---
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Paralegal AI',
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: kAccentColor,
          brightness: Brightness.dark,
          primary: kAccentColor,
          secondary: kUserBubbleColor,
          background: kBgDark,
          surface: kAiBubbleColor,
        ),
        textTheme: GoogleFonts.poppinsTextTheme(ThemeData.dark().textTheme)
            .apply(bodyColor: kTextColor, displayColor: kTextColor),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0x33FFFFFF),
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.6)),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30.0),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30.0),
            borderSide: BorderSide(color: kAccentColor, width: 1.5),
          ),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
        ),
        iconButtonTheme: IconButtonThemeData(
            style: IconButton.styleFrom(
              foregroundColor: kAccentColor,
              backgroundColor: Colors.white.withOpacity(0.2),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(15)
              )
            )
        ),
        chipTheme: ChipThemeData(
          backgroundColor: kSourceChipColor,
          labelStyle: TextStyle(color: kSourceChipTextColor, fontSize: 11, fontWeight: FontWeight.w500),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20)
          )
        )
      ),
      home: const MyHomePage(title: 'Paralegal AI Interface'),
    );
  }
}

// --- MyHomePage State (Manages view switching) ---
class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;
  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  bool _isInChatView = false; // <<< State to track view mode
  String? _initialQuery; // <<< To store the first query

  // --- Callback function to switch to chat view ---
  void _startChatView(String query) {
    if (query.trim().isNotEmpty) {
      setState(() {
        _initialQuery = query.trim();
        _isInChatView = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity, // Ensure Container fills width
        height: double.infinity, // Ensure Container fills height
        decoration:  BoxDecoration(
          color: kBgDark
          // gradient: LinearGradient(
          //   colors: [kBgDark, kBgLight],
          //   begin: Alignment.topLeft,
          //   end: Alignment.bottomRight,
          // ),
        ),
        // --- Animated Switcher for Smooth Transition ---
        child: AnimatedSwitcher(
          duration: kTransitionDuration, // Use the defined duration
          transitionBuilder: (Widget child, Animation<double> animation) {
            // Fade transition
            return FadeTransition(opacity: animation, child: child);
            // Or Slide transition:
            // return SlideTransition(
            //   position: Tween<Offset>(
            //     begin: const Offset(0.0, 0.3), // Slide up from bottom slightly
            //     end: Offset.zero,
            //   ).animate(animation),
            //   child: child,
            // );
          },
          child: _isInChatView
              ? _buildChatView(context, _initialQuery!) // Pass initial query
              : _buildInitialSearchView(context), // Build initial view
        ),
      ),
    );
  }

  // --- Builds the Initial Search View ---
  Widget _buildInitialSearchView(BuildContext context) {
    final TextEditingController initialInputController = TextEditingController();

    return KeyedSubtree( // Use Key to ensure state resets if needed
      key: const ValueKey('InitialView'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center, // Center vertically
          children: <Widget>[
            // --- App Title / Logo Area ---
            Text(
              'Paralegal',
              textAlign: TextAlign.center,
              style: GoogleFonts.exo2(
                fontSize: 60, // Larger font size for initial view
                fontWeight: FontWeight.w600,
                color: Colors.white.withOpacity(0.9),
                letterSpacing: 1.5,
                shadows: [
                  Shadow(
                      blurRadius: 10.0,
                      color: Colors.black.withOpacity(0.3),
                      offset: Offset(2.0, 2.0))
                ]
              ),
            ).animate().fadeIn(delay: 300.ms, duration: 600.ms), // Simple fade-in
            const SizedBox(height: 15),
             Text(
              'Ask me about Toronto Municipal Code Bylaws',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 16,
                fontWeight: FontWeight.w300,
                color: Colors.white.withOpacity(0.7),
              ),
            ).animate().fadeIn(delay: 500.ms, duration: 600.ms),
            const SizedBox(height: 50), // Space before input

            // --- Search Input Row ---
             ClipRRect( // Add slight frost effect to input area
                 borderRadius: BorderRadius.circular(30),
                 child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 5.0, sigmaY: 5.0),
                    child: Container(
                      padding: EdgeInsets.only(left: 5, right: 5, top: 5, bottom: 5),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(30),
                        border: Border.all(color: Colors.white.withOpacity(0.2))
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              

                              controller: initialInputController,
                              style: const TextStyle(color: kTextColor, fontSize: 16),
                              decoration: InputDecoration(
                                border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30.0),
                        // Use BorderSide.none to avoid drawing a line here
                        borderSide: BorderSide.none,
                    ),
                    enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30.0),
                        borderSide: BorderSide.none,
                    ),
                    // Keep the accent color border on focus (optional but good UX)
                    focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30.0),
                        borderSide: BorderSide(color: kAccentColor, width: 1.5),
                    ),
                     // Define error/disabled borders for completeness if needed
                    errorBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30.0),
                        borderSide: BorderSide(color: Colors.redAccent, width: 1.5),
                    ),
                     disabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(30.0),
                        borderSide: BorderSide.none,
                    ),
                                hintText: 'e.g., rules about noise after 11 PM?',
                                // border: InputBorder.none, // Remove internal border
                                // focusedBorder: InputBorder.none,
                                // enabledBorder: InputBorder.none,
                                // errorBorder: InputBorder.none,
                                // disabledBorder: InputBorder.none,
                                hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                                contentPadding: EdgeInsets.symmetric(horizontal: 25, vertical: 18) // Adjust padding
                              
                              ),
                              onSubmitted: (value) => _startChatView(value), // Trigger on enter
                            ),
                          ),
                          SizedBox(width: 8),
                          IconButton(
                            icon: const Icon(Icons.send_rounded),
                            iconSize: 24,
                            tooltip: 'Start Search',
                            onPressed: () => _startChatView(initialInputController.text), // Trigger on button press
                            // Style comes from theme
                          ),
                          const SizedBox(width: 5), // Padding for button inside container
                        ],
                      ),
                    ),
                 ),
             ).animate().slideY(begin: 0.2, delay: 700.ms, duration: 500.ms).fadeIn(), // Slide/fade in input

            const SizedBox(height: 150), // Push input up from bottom
          ],
        ),
      ),
    );
  }

  // --- Builds the Main Chat View ---
  Widget _buildChatView(BuildContext context, String initialQuery) {
    // Use KeyedSubtree to ensure ChatWindow gets rebuilt correctly
    // if we were to switch back and forth (though we aren't here)
    return KeyedSubtree(
      key: const ValueKey('ChatView'),
      child: Column(
        children: [
          _buildCustomAppBar(context), // Keep the AppBar
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withOpacity(0.1), width: 1.5),
                  ),
                  // <<< Pass the initialQuery to ChatWindow >>>
                  child: ChatWindow(initialQuery: initialQuery),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- Custom AppBar Widget (Unchanged) ---
  Widget _buildCustomAppBar(BuildContext context) {
    return SafeArea( // Ensures content is below status bar etc.
      child: Container(
         padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15.0),
         decoration: BoxDecoration(
           color: Colors.transparent,
           border: Border(
             bottom: BorderSide(color: Colors.white.withOpacity(0.2), width: 1),
           )
         ),
         child: Row(
           mainAxisAlignment: MainAxisAlignment.spaceBetween,
           children: [
              Image.asset(
                'assets/Google_Gemini_logo.png',
                height: 35,
                color: Colors.white.withOpacity(0.8),
              ),
              Text(
                'Paralegal',
                style: GoogleFonts.exo2(
                  fontSize: 36,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                  letterSpacing: 1.2
                ),
              ),
              Image.asset(
                'assets/MongoDB_Logo.png',
                height: 35,
                 color: Colors.white.withOpacity(0.8),
              ),
           ],
         ),
      ),
    );
  }
}


// -------------------- Chat message model (Unchanged) --------------------
class ChatMessage {
  final String text;
  final DateTime time;
  final bool fromMe; // true = user, false = server
  final List<Map<String, dynamic>>? sources;
  final bool isLoading; // For loading state

  ChatMessage({
    required this.text,
    required this.time,
    required this.fromMe,
    this.sources,
    this.isLoading = false,
  });
}

// ------------- Chat window -------------
class ChatWindow extends StatefulWidget {
  // <<< Add optional initialQuery parameter >>>
  final String? initialQuery;

  const ChatWindow({super.key, this.initialQuery});

  @override
  State<ChatWindow> createState() => _ChatWindowState();
}

class _ChatWindowState extends State<ChatWindow> {
  final _messages = <ChatMessage>[];
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _canSend = true;
  static const _cooldown = Duration(seconds: 3);
  // No longer need _lastMessage here, send handles current input

  @override
  void initState() {
    super.initState();
    // Use WidgetsBinding to interact safely after the first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // <<< Handle the initial query if provided >>>
      if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
        _processQuery(widget.initialQuery!);
      } else {
         // Only add the welcome message if no initial query was given
        if(mounted) {
          setState(() {
              _messages.add(
                ChatMessage(
                  text: "Hello! How can I help you with Toronto bylaws today?",
                  time: DateTime.now(),
                  fromMe: false,
                )
              );
          });
        }
      }
    });
  }

  // --- Refactored query processing logic ---
  Future<void> _processQuery(String query) async {
     if (query.isEmpty) return;

    // Add user message
    if(mounted) { // Check if widget is still in the tree
        setState(() {
          _messages.add(
            ChatMessage(text: query, time: DateTime.now(), fromMe: true),
          );
          _canSend = false; // Start cooldown (applies even for initial query)
        });
        _scrollToBottom();
    }


    // Add AI loading message
    final loadingMessageIndex = _messages.length;
    if(mounted) {
        setState(() {
          _messages.add(ChatMessage(
            text: "...",
            time: DateTime.now(),
            fromMe: false,
            isLoading: true
            ));
        });
        _scrollToBottom();
    }

    // --- API Call ---
    // Ensure requestAPI uses the correct IP
    final apiResult = await requestAPI(query);
    final aiText = apiResult['ai_response'] as String;
    final rawSources = apiResult['retrieved_sources'] as List<Map<String, dynamic>>;

    final seenTitles = <String>{};
    final sources = rawSources.where((source) {
      final title = source['title'];
      if (title == null || seenTitles.contains(title)) {
        return false;
      }
      seenTitles.add(title);
      return true;
    }).toList();

    // // Convert each map to JSON string, put in a Set to remove dupes, then decode back
    // final sources = rawSources
    //     .map((e) => jsonEncode(e))
    //     .toSet()
    //     .map((e) => jsonDecode(e) as Map<String, dynamic>)
    //     .toList();

    // --- Update Message List ---
     if(mounted) {
      setState(() {
        // Replace the loading message
        if (loadingMessageIndex < _messages.length && _messages[loadingMessageIndex].isLoading) {
          _messages[loadingMessageIndex] = ChatMessage(
              text: aiText,
              time: DateTime.now(),
              fromMe: false,
              sources: sources,
              isLoading: false,
          );
        } else {
          _messages.add(ChatMessage(
              text: aiText,
              time: DateTime.now(),
              fromMe: false,
              sources: sources,
          ));
        }
        // Re-enable send button after cooldown
        Timer(_cooldown, () {
            if(mounted) { setState(() => _canSend = true); }
        });
      });
      _scrollToBottom(isDelayed: true);
    }
  }

  // --- Send function (now simpler, just calls _processQuery) ---
  void _send() {
    if (!_canSend || _input.text.trim().isEmpty) return;
    final text = _input.text.trim();
    _input.clear();
    _processQuery(text); // Use the refactored logic
  }

  // --- API helper (Unchanged - MAKE SURE IP IS CORRECT) ---
  Future<Map<String, dynamic>> requestAPI(String query) async {
      // final uri = Uri.parse('http://172.20.10.2:5000/api/query'); // Use your correct IP
      // final uri = Uri.parse('http://127.0.0.1:5000/api/query'); // Common localhost IP
      final uri = Uri.parse('https://paralegalbylaw.org/api/query');

      try {
        final res = await http.post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'query': query}),
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
          print('Server Error ${res.statusCode}: ${res.reasonPhrase}'); // Log error
          return {
            'ai_response': '⚠️ Server Error ${res.statusCode}. Please check connection or try again later.',
            'retrieved_sources': <Map<String, dynamic>>[],
          };
        }
      } catch (e) {
        print('Network/Request Error, sorry :/'); // Log error
        return {
          'ai_response': '⚠️ Network Error. Could not connect to the server. Please check your connection or ensure the server is running.',
          'retrieved_sources': <Map<String, dynamic>>[],
        };
      }
    }

  // Helper function to scroll to bottom (Unchanged)
  void _scrollToBottom({bool isDelayed = false}) {
     Future.delayed(Duration(milliseconds: isDelayed ? 100 : 0)).then((_) {
        if (_scroll.hasClients) {
          _scroll.animateTo(
            _scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
     });
  }

  // ============================== UI BUILD ===============================
   @override
  Widget build(BuildContext context) {
    // The structure inside ChatWindow remains the same
    return Column(
      children: [
        // --- Message List ---
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            itemCount: _messages.length,
            padding: const EdgeInsets.symmetric(vertical: 15.0, horizontal: 10.0),
            itemBuilder: (context, i) {
              final m = _messages[i];
              // Add animation only after initial build if desired
              // For simplicity, animating all messages including initial ones
              return _buildMessageItem(context, m)
                  .animate()
                  .fadeIn(duration: kAnimationDuration)
                  .slideY(begin: 0.2, duration: kAnimationDuration, curve: Curves.easeOutCubic);
            },
          ),
        ),
        // --- Input Area ---
        _buildInputArea(context),
      ],
    );
  }

 // --- UI HELPER WIDGETS (_buildMessageItem, _buildMessageBubble, _buildSourcesSection, _buildSourceChip, _buildInputArea) are UNCHANGED from the previous version ---
 // Keep the helper widgets exactly as they were in the previous "flashy" version
 // ... (paste the _buildMessageItem, _buildMessageBubble, _buildSourcesSection, _buildSourceChip, _buildInputArea methods here) ...

 //--------------------------------------------------//
 //           UI HELPER WIDGETS (Paste from previous answer) //
 //--------------------------------------------------//

 // Builds a single message row (icon + bubble + sources)
 Widget _buildMessageItem(BuildContext context, ChatMessage message) {
    final bool isUser = message.fromMe;
    final alignment = isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final marginEdge = isUser ? EdgeInsets.only(left: 40.0) : EdgeInsets.only(right: 40.0);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0).add(marginEdge),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
           Row(
             mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
             crossAxisAlignment: CrossAxisAlignment.start, // Align icon top with bubble top
             children: [
                // Icon (Conditional)
                if (!isUser) ...[
                  Icon(Icons.description, color: kAccentColor.withOpacity(0.8), size: 24),
                  const SizedBox(width: 8),
                ],

                // Message Bubble (Flexible to take available space)
                Flexible( // Important for text wrapping
                   child: _buildMessageBubble(context, message)
                ),

                // Icon (Conditional)
                if (isUser) ...[
                  const SizedBox(width: 8),
                  Icon(Icons.person_outline, color: Colors.white.withOpacity(0.8), size: 24),
                ],
              ],
           ),
           // Sources (Only for AI messages)
           if (!isUser && message.sources != null && message.sources!.isNotEmpty && !message.isLoading)
              _buildSourcesSection(context, message.sources!),
        ],
      ),
    );
 }

 // Builds the message bubble with frosted glass effect
 Widget _buildMessageBubble(BuildContext context, ChatMessage message) {
   final bool isUser = message.fromMe;
   final bubbleColor = isUser ? kUserBubbleColor : kAiBubbleColor;
   final borderRadius = BorderRadius.only(
     topLeft: const Radius.circular(18),
     topRight: const Radius.circular(18),
     bottomLeft: Radius.circular(isUser ? 18 : 4),
     bottomRight: Radius.circular(isUser ? 4 : 18),
   );

   return ClipRRect( // Clip for the blur effect
     borderRadius: borderRadius,
     child: BackdropFilter( // Apply frosted glass
       filter: ImageFilter.blur(sigmaX: 8.0, sigmaY: 8.0),
       child: Container(
         padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
         decoration: BoxDecoration(
           color: bubbleColor,
           borderRadius: borderRadius,
         ),
         child: message.isLoading // Show loading indicator if needed
             ? Center(
                child: LoadingAnimationWidget.threeArchedCircle(
                  color: kAccentColor,
                  size: 25,
                ),
             )
             : MarkdownBody( // Use MarkdownBody for AI response
                 data: message.text,
                 selectable: true,
                 styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)).copyWith(
                     p: Theme.of(context).textTheme.bodyMedium?.copyWith(color: kTextColor, height: 1.4), // Ensure text color and line height
                     a: TextStyle(color: kAccentColor, decoration: TextDecoration.underline, decorationColor: kAccentColor), // Style links
                 ),
                 onTapLink: (text, href, title) {
                    if(href != null) _launchUrl(href);
                 },
               ),
       ),
     ),
   );
 }

 // --- Builds the sources section below AI bubble ---
 Widget _buildSourcesSection(BuildContext context, List<Map<String, dynamic>> sources) {
   final sourcesToDisplay = sources.take(5).toList(); // Show max 5 sources

   return Padding(
     padding: const EdgeInsets.only(top: 8.0, left: 32.0), // Indent sources slightly
     child: Wrap( // Use Wrap for responsiveness if many sources
       spacing: 8.0, // Horizontal gap between chips
       runSpacing: 4.0, // Vertical gap between lines of chips
       children: sourcesToDisplay.map((source) => _buildSourceChip(context, source)).toList(),
     ),
   );
 }

 // --- Builds a single clickable source Chip ---
 Widget _buildSourceChip(BuildContext context, Map<String, dynamic> source) {
   final String title = source['title'] ?? 'Source';
   final String bylawId = source['bylaw_id']?.replaceFirst('Chapter ', '') ?? '';
   final String pdfUrl = source['pdf_url'] ?? '';
   final displayId = bylawId.isNotEmpty ? "($bylawId)" : "";
   final displayText = "$title $displayId".trim(); // Ensure no extra space if ID is empty

   return ActionChip(
    color: WidgetStatePropertyAll(Colors.white.withAlpha(200)),
     avatar: Icon(Icons.link, size: 16, color: kSourceChipTextColor.withOpacity(0.8)),
     label: Text(displayText),
     tooltip: 'Open source: $displayText',
     onPressed: pdfUrl.isNotEmpty ? () => _launchUrl(pdfUrl) : null,
   );
 }


 // --- Builds the bottom input area ---
 Widget _buildInputArea(BuildContext context) {
   return ClipRRect(
     child: BackdropFilter(
       filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
       child: Container(
         padding: const EdgeInsets.symmetric(horizontal: 15.0, vertical: 10.0).copyWith(bottom: 20),
         decoration: BoxDecoration(
           color: Colors.black.withOpacity(0.2),
         ),
         child: Row(
           children: [
             Expanded(
               child: TextField(
                 controller: _input,
                 onSubmitted: (_) => _send(), // Use _send for subsequent messages
                 style: TextStyle(color: kTextColor),
                 decoration: const InputDecoration(
                   hintText: 'Ask a follow-up question...', // Updated hint text
                 ),
               ),
             ),
             const SizedBox(width: 10),
             IconButton(
               icon: AnimatedSwitcher(
                 duration: const Duration(milliseconds: 200),
                 transitionBuilder: (child, animation) {
                   return ScaleTransition(scale: animation, child: child);
                 },
                 child: Icon(
                   _canSend ? Icons.send_rounded : Icons.hourglass_empty_rounded,
                   key: ValueKey<bool>(_canSend),
                   color: _canSend ? kAccentColor : Colors.grey.shade500,
                   size: 24,
                 ),
               ),
               tooltip: _canSend ? 'Send message' : 'Please wait...',
               onPressed: _canSend ? _send : null,
             ),
           ],
         ),
       ),
     ),
   );
 }


 // --- Launches the URL --- (Unchanged)
 Future<void> _launchUrl(String urlString) async {
    final Uri url = Uri.parse(urlString);
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      if (mounted) {
         ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
                content: Text('Could not open link: $urlString'),
                backgroundColor: Colors.redAccent,
            ),
          );
      }
      print('Could not launch $urlString');
    }
  }
// --- End of _ChatWindowState class ---
}
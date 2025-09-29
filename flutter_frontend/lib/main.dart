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
import 'widgets/app_header.dart';
// import 'widgets/about_dialog.dart';
import 'widgets/info_section.dart';
import 'widgets/about_dialog.dart' as deprecated_about;
import 'widgets/about_page.dart';
import 'widgets/disclaimer.dart';
import 'widgets/title_text.dart';
import 'package:flutter/services.dart';

// --- Constants (Keep these the same) ---
Color kBgDark = Colors.grey[900]!;
const Color kBgLight = Color(0xFF3F51B5); // Indigo
const Color kAccentColor = Color(0xFF00BCD4); // Cyan
const Color kUserBubbleColor = Color(0x77FFFFFF); // Semi-transparent white
const Color kAiBubbleColor = Color(0x55000000); // Semi-transparent dark
const Color kTextColor = Colors.white;
const Color kSourceChipColor = Color(0xFFB2EBF2); // Light Cyan
const Color kSourceChipTextColor = Colors.black87;
const Duration kAnimationDuration = Duration(milliseconds: 400);
const Duration kTransitionDuration = Duration(milliseconds: 500);

void main() => runApp(const MyApp());

// --- MyApp (Theme setup - largely unchanged) ---
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      //builder: (context, child) => SelectionArea(child: child ?? const SizedBox.shrink()),
      title: 'Paralegal AI',
      routes: {
        '/about': (context) => const AboutPage(),
      },
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
      home: const MyHomePage(title: 'Paralegal AI'),
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
  bool _isInChatView = false;
  String? _initialQuery;
  String _selectedCity = 'Toronto'; // Track selected city

  int _chatEpoch = 0;

  // Available cities for expansion
  final List<String> _availableCities = ['Toronto', 'Waterloo', 'Guelph'];

  Future<bool> _confirmResetChat(BuildContext context, String newCity) async {
    if (!_isInChatView) return true; // no chat open — OK to switch silently
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Switch city?'),
            content: Text(
              'You’re currently chatting about $_selectedCity.\n'
              'Switching to $newCity will clear this conversation.'
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(false),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(ctx).pop(true),
                child: const Text('Switch & Reset'),
              ),
            ],
          ),
        ) ??
        false;
  }


  void _openRequestCitySheet(BuildContext context) {
    final _cityCtrl = TextEditingController();
    final _emailCtrl = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.blueGrey[900],
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
            left: 20, right: 20, top: 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.location_city_outlined),
                  const SizedBox(width: 8),
                  const Text('Request a city', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.of(ctx).pop(), icon: const Icon(Icons.close))
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _cityCtrl,
                decoration: const InputDecoration(
                  labelText: 'City name',
                  hintText: 'e.g., Waterloo, Ontario',
                ),
                inputFormatters: [
                  LengthLimitingTextInputFormatter(50), // max 50 chars
                ],
                autofocus: true,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email (optional)',
                  hintText: 'We’ll contact you when it’s ready',
                ),
                inputFormatters: [
                  LengthLimitingTextInputFormatter(50), // max 50 chars
                ],
              ),
              
              const SizedBox(height: 16),
              Row(
                children: [
                  ElevatedButton.icon(
                    onPressed: () async {
                      final city = _cityCtrl.text.trim();
                      final email = _emailCtrl.text.trim();
                      if (city.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Please enter a city name'))
                        );
                        return;
                      }
                      try {
                        final uri = Uri.parse('https://api.paralegalbylaw.org/api/request-city');
                        final res = await http.post(
                          uri,
                          headers: {'Content-Type': 'application/json'},
                          body: jsonEncode({'city': city, if (email.isNotEmpty) 'email': email }),
                        );
                        if (res.statusCode >= 200 && res.statusCode < 300) {
                          if (context.mounted) {
                            Navigator.of(ctx).pop();
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Thanks! We’ve received your request for "$city".'))
                            );
                          }
                        } else {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Request failed (${res.statusCode}). Try again later.'))
                            );
                          }
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Network error. Please try again.'))
                          );
                        }
                      }
                    },
                    icon: const Icon(Icons.send),
                    label: const Text('Submit'),
                  ),
                  const SizedBox(width: 12),
                  TextButton(
                    onPressed: () => Navigator.of(ctx).pop(),
                    child: const Text('Cancel'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
  }


  // --- Callback function to switch to chat view ---
  void _startChatView(String query) {
    if (query.trim().isNotEmpty) {
      setState(() {
        _initialQuery = query.trim();
        _isInChatView = true;
      });
    }
  }

  // --- Callback to handle city selection ---
  void _onCityChanged(String newCity) async {
    if (newCity == _selectedCity) return;

    // Ask for confirmation if chat is active
    final bool ok = await _confirmResetChat(context, newCity);
    if (!ok) return; // User cancelled

    setState(() {
      _selectedCity = newCity;
      _chatEpoch++; // Force ChatWindow to remount with fresh state
    });
  }

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: Scaffold(
        body: Container(
          width: double.infinity,
          height: double.infinity,
          decoration: BoxDecoration(color: kBgDark),
          child: Column(
            children: [
              // --- Enhanced Header ---
              AppHeader(
                selectedCity: _selectedCity,
                availableCities: _availableCities,
                onCityChanged: _onCityChanged,
                isInChatView: _isInChatView,
                onLogoTap: () { setState(() { _isInChatView = false; _initialQuery = ''; }); },
              ),
              // --- Main Content ---
              Expanded(
                child: AnimatedSwitcher(
                  duration: kTransitionDuration,
                  transitionBuilder: (Widget child, Animation<double> animation) {
                    return FadeTransition(opacity: animation, child: child);
                  },
                  child: _isInChatView
                      ? _buildChatView(context, _initialQuery!)
                      : _buildInitialSearchView(context),
                ),
              ),
              // --- Disclaimer Footer ---
              DisclaimerFooter(),
            ],
          ),
        ),
      ),
    );
  }

  // --- Builds the Initial Search View ---
  Widget _buildInitialSearchView(BuildContext context) {
    final TextEditingController initialInputController = TextEditingController();

    return KeyedSubtree(
      key: const ValueKey('InitialView'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return SingleChildScrollView(
            padding: EdgeInsets.only(bottom: 24),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight - 24),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    // // --- App Title / Logo Area ---
                    // Text(
                    //   'Paralegal AI',
                    //   textAlign: TextAlign.center,
                    //   style: GoogleFonts.exo2(
                    //     fontSize: 52,
                    //     fontWeight: FontWeight.w600,
                    //     color: Colors.white.withOpacity(0.9),
                    //     letterSpacing: 1.5,
                    //     shadows: [
                    //       Shadow(
                    //           blurRadius: 10.0,
                    //           color: Colors.black.withOpacity(0.3),
                    //           offset: Offset(2.0, 2.0))
                    //     ]
                    //   ),
                    // ).animate().fadeIn(delay: 300.ms, duration: 600.ms),
            
                    const SizedBox(height: 45),
            
                    TitleText().animate().fadeIn(delay: 400.ms, duration: 600.ms),

                    const SizedBox(height: 15),

                    Text(
                      "Ask about your city's bylaws like you'd ask a friend — we'll handle the search.",
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w400,
                        fontSize: 18,
                      ),
                      textAlign: TextAlign.center,
                    ).animate().fadeIn(delay:600.ms, duration: 600.ms),


                    
                    const SizedBox(height: 30),
                  
                    // --- Info Section ---
                    InfoSection().animate().fadeIn(delay: 500.ms, duration: 600.ms),
                    
                    const SizedBox(height: 40),

                    // --- Search Input Row ---
                   
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [Colors.cyan.withAlpha(188), Colors.tealAccent.withAlpha(188)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: const [
                          BoxShadow(
                            color: Colors.black26,
                            blurRadius: 6,
                            offset: Offset(0, 3),
                          ),
                        ],
                      ),
                      child: ElevatedButton.icon(
                        onPressed: () {
                          setState(() {
                            _isInChatView = true;
                            _initialQuery = initialInputController.text.trim();
                          });
                        },

                        label: const Text('Try it Now'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 20),
                          textStyle: const TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                          ),
                          // shape: RoundedRectangleBorder(
                          //   //borderRadius: BorderRadius.circular(12),
                          // ),
                          backgroundColor: Colors.transparent, // make button itself transparent
                          shadowColor: Colors.transparent, // avoid double shadows
                          foregroundColor: Colors.white, // text & icon color
                        ),
                      ),
                    ),

                    const SizedBox(height: 8),

                    Text(
                      "Always 100% free, No Signup",
                      style: TextStyle(
                        color: Colors.white.withAlpha(200),
                        fontSize: 12
                      )
                    ),



                    const SizedBox(height: 100),
                  ],
                ),
              ),
            )
          );
        }
      )
    );
  }

  // --- Builds the Main Chat View ---
  Widget _buildChatView(BuildContext context, String initialQuery) {
    return KeyedSubtree(
      key: ValueKey('ChatView-${_selectedCity}-$_chatEpoch'),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: ChatWindow(
              key: ValueKey('ChatWindow-${_selectedCity}-$_chatEpoch'), // <— NEW
              initialQuery: initialQuery,
              selectedCity: _selectedCity,
            ),
          ),
        ),
    );
  }
}

// -------------------- Chat message model (Enhanced) --------------------
class ChatMessage {
  final String text;
  final DateTime time;
  final bool fromMe;
  final List<Map<String, dynamic>>? sources;
  final bool isLoading;
  final Map<String, dynamic>? context; // Additional context for conversation

  ChatMessage({
    required this.text,
    required this.time,
    required this.fromMe,
    this.sources,
    this.isLoading = false,
    this.context,
  });
}

// ------------- Chat window -------------
class ChatWindow extends StatefulWidget {
  final String? initialQuery;
  final String selectedCity;

  const ChatWindow({super.key, this.initialQuery, this.selectedCity = 'Toronto'});

  @override
  State<ChatWindow> createState() => _ChatWindowState();
}

class _ChatWindowState extends State<ChatWindow> {
  final _messages = <ChatMessage>[];
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _canSend = true;
  static const _cooldown = Duration(seconds: 3);

  Widget _introMessage(String city) {
    return RichText(
      text: TextSpan(
        style: TextStyle(
          fontSize: 16,
          color: Colors.white,
          height: 1.4,
        ),
        children: [
          const TextSpan(text: "Hello! I'm your AI assistant for "),
          WidgetSpan(
            child: ShaderMask(
              shaderCallback: (bounds) => LinearGradient(
                colors: [Colors.cyan, Colors.tealAccent],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ).createShader(bounds),
              child: Text(
                city,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white, // will be masked
                ),
              ),
            ),
          ),
          const TextSpan(
              text:
                  " municipal bylaws. I can help you understand noise regulations, "
                  "parking rules, zoning restrictions, and much more. What would you like to know?"),
        ],
      ),
    );
  }


  // @override
  // void didUpdateWidget(covariant ChatWindow oldWidget) {
  //   super.didUpdateWidget(oldWidget);
  //   if (oldWidget.selectedCity != widget.selectedCity) {
  //     setState(() {
  //       if (_messages.isNotEmpty && !_messages.first.fromMe) {
  //         _messages[0] = ChatMessage(
  //           text: "", // leave text empty, we’ll render via custom builder
  //           time: DateTime.now(),
  //           fromMe: false,
  //           context: {'introCity': widget.selectedCity},
  //         );

  //       }
  //     });
  //   }
  // }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.initialQuery != null && widget.initialQuery!.isNotEmpty) {
        _processQuery(widget.initialQuery!);
      } else {
        if(mounted) {
          setState(() {
            _messages.add(
              ChatMessage(
                text: "", // leave empty, handled by custom renderer
                time: DateTime.now(),
                fromMe: false,
                context: {'introCity': widget.selectedCity},
              ),
            );
          });

        }
      }
    });
  }

  // --- Enhanced query processing with context ---
  Future<void> _processQuery(String query) async {
     if (query.isEmpty) return;

    // Build conversation context
    final conversationContext = _messages
    .where((msg) => !msg.isLoading)
    .map((msg) => {
      'fromMe': msg.fromMe,
      'text': msg.text,
      'timestamp': msg.time.toIso8601String(),
    })
    .toList();


    if(mounted) {
        setState(() {
          _messages.add(
            ChatMessage(
              text: query, 
              time: DateTime.now(), 
              fromMe: true,
              context: {'city': widget.selectedCity}
            ),
          );
          _canSend = false;
        });
        _scrollToBottom();
    }

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

    // --- Enhanced API Call with context ---
    final apiResult = await requestAPI(query, conversationContext);
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

     if(mounted) {
      setState(() {
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
        Timer(_cooldown, () {
            if(mounted) { setState(() => _canSend = true); }
        });
      });
      _scrollToBottom(isDelayed: true);
    }
  }

  void _send() {
    if (!_canSend || _input.text.trim().isEmpty) return;
    final text = _input.text.trim();
    _input.clear();
    _processQuery(text);
  }

  // --- Enhanced API helper with context ---
  Future<Map<String, dynamic>> requestAPI(String query, List<Map<String, dynamic>> context) async {
      final uri = Uri.parse('https://api.paralegalbylaw.org/api/query');

      try {
        final res = await http.post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'query': query,
            'city': widget.selectedCity,
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
          print('Server Error ${res.statusCode}: ${res.reasonPhrase}');
          return {
            'ai_response': '⚠️ Server Error ${res.statusCode}. Please check connection or try again later.',
            'retrieved_sources': <Map<String, dynamic>>[],
          };
        }
      } catch (e) {
        print('Network/Request Error, sorry :/');
        return {
          'ai_response': '⚠️ Network Error. Could not connect to the server. Please check your connection or ensure the server is running.',
          'retrieved_sources': <Map<String, dynamic>>[],
        };
      }
    }

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

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scroll,
            itemCount: _messages.length,
            padding: const EdgeInsets.symmetric(vertical: 15.0, horizontal: 10.0),
            itemBuilder: (context, i) {
              final m = _messages[i];
              return _buildMessageItem(context, m)
                  .animate()
                  .fadeIn(duration: kAnimationDuration)
                  .slideY(begin: 0.2, duration: kAnimationDuration, curve: Curves.easeOutCubic);
            },
          ),
        ),
        _buildInputArea(context),
      ],
    );
  }

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
             crossAxisAlignment: CrossAxisAlignment.start,
             children: [
                if (!isUser) ...[
                  Icon(Icons.description, color: kAccentColor.withOpacity(0.8), size: 24),
                  const SizedBox(width: 8),
                ],

                Flexible(
                   child: _buildMessageBubble(context, message)
                ),

                if (isUser) ...[
                  const SizedBox(width: 8),
                  Icon(Icons.person_outline, color: Colors.white.withOpacity(0.8), size: 24),
                ],
              ],
           ),
           if (!isUser && message.sources != null && message.sources!.isNotEmpty && !message.isLoading)
              _buildSourcesSection(context, message.sources!),
        ],
      ),
    );
 }

  Widget _buildMessageBubble(BuildContext context, ChatMessage message) {
    final bool isUser = message.fromMe;
    final bubbleColor = isUser ? kUserBubbleColor : kAiBubbleColor;
    final borderRadius = BorderRadius.only(
      topLeft: const Radius.circular(18),
      topRight: const Radius.circular(18),
      bottomLeft: Radius.circular(isUser ? 18 : 4),
      bottomRight: Radius.circular(isUser ? 4 : 18),
    );

    final introCity = message.context?['introCity'];

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8.0, sigmaY: 8.0),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: bubbleColor,
            borderRadius: borderRadius,
          ),
          child: message.isLoading
              ? const Center(child: LoadingMessage())
              : introCity != null
                  ? _introMessage(introCity) // render the gradient intro
                  : MarkdownBody(
                      data: message.text,
                      selectable: true,
                      styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context))
                          .copyWith(
                        p: Theme.of(context)
                            .textTheme
                            .bodyLarge
                            ?.copyWith(color: kTextColor, height: 1.4),
                        a: TextStyle(
                          color: kAccentColor,
                          decoration: TextDecoration.underline,
                          decorationColor: kAccentColor,
                        ),
                      ),
                      onTapLink: (text, href, title) {
                        if (href != null) _launchUrl(href);
                      },
                    ),
        ),
      ),
    );
  }


 Widget _buildSourcesSection(BuildContext context, List<Map<String, dynamic>> sources) {
   final sourcesToDisplay = sources.take(5).toList();

   return Padding(
     padding: const EdgeInsets.only(top: 8.0, left: 32.0),
     child: Wrap(
       spacing: 8.0,
       runSpacing: 4.0,
       children: sourcesToDisplay.map((source) => _buildSourceChip(context, source)).toList(),
     ),
   );
 }

 Widget _buildSourceChip(BuildContext context, Map<String, dynamic> source) {
   final String title = source['title'] ?? 'Source';
   final String bylawId = source['bylaw_id']?.replaceFirst('Chapter ', '') ?? '';
   final String pdfUrl = source['pdf_url'] ?? '';
   final displayId = bylawId.isNotEmpty ? "($bylawId)" : "";
   final displayText = "$title $displayId".trim();

   return ActionChip(
    color: WidgetStatePropertyAll(Colors.white.withAlpha(200)),
     avatar: Icon(Icons.link, size: 16, color: kSourceChipTextColor.withOpacity(0.8)),
     label: Text(displayText),
     tooltip: 'Open source: $displayText',
     onPressed: pdfUrl.isNotEmpty ? () => _launchUrl(pdfUrl) : null,
   );
 }


 Widget _buildInputArea(BuildContext context) {
   return ClipRRect(
     child: BackdropFilter(
       filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
       child: Container(
         padding: const EdgeInsets.symmetric(horizontal: 15.0, vertical: 10.0).copyWith(bottom: 20),
        //  decoration: BoxDecoration(
        //    color: Colors.black.withOpacity(0.2),
        //  ),
         child: Row(
           children: [
             Expanded(
               child: TextField(
                 controller: _input,
                 onSubmitted: (_) => _send(),
                 style: TextStyle(color: kTextColor),
                 decoration: const InputDecoration(
                   hintText: 'Ask a question...',
                 ),
                 inputFormatters: [
                  LengthLimitingTextInputFormatter(500), // max 50 chars
                ],
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
}


const loadingSteps = [
  "Searching bylaws...",
  "Analyzing relevant sections...",
  "Generating natural language response...",
];


class LoadingMessage extends StatefulWidget {
  const LoadingMessage({super.key});

  @override
  State<LoadingMessage> createState() => _LoadingMessageState();
}

class _LoadingMessageState extends State<LoadingMessage> {
  int index = 0;
  late final Timer timer;

  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 2), (t) {
      setState(() {
        index = (index + 1) % loadingSteps.length;
      });
    });
  }

  @override
  void dispose() {
    timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      loadingSteps[index],
      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: kAccentColor,
            fontStyle: FontStyle.italic,
          ),
    );
  }
}

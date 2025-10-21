import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../widgets/shared/app_header.dart';
import '../widgets/shared/info_section.dart';
import '../widgets/shared/about_dialog.dart' as deprecated_about;
import '../widgets/shared/about_page.dart';
import '../widgets/shared/disclaimer.dart';
import '../widgets/shared/title_text.dart';
import '../screens/chat_window.dart';

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  bool _isInChatView = false;
  String? _initialQuery;
  String _selectedCity = 'Waterloo';
  int _chatEpoch = 0;

  String _selectedPage = 'home'; // can be 'home' or 'about'


  Future<bool> _confirmResetChat(BuildContext context, String newCity) async {
    if (!_isInChatView) return true;
    return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Switch city?'),
            content: Text('You’re currently chatting about $_selectedCity.\nSwitching to $newCity will clear this conversation.'),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
              ElevatedButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Switch & Reset')),
            ],
          ),
        ) ??
        false;
  }

  void _onCityChanged(String newCity) async {
    if (newCity == _selectedCity) return;
    final ok = await _confirmResetChat(context, newCity);
    if (!ok) return;
    setState(() {
      _selectedCity = newCity;
      _chatEpoch++; // force remount of ChatWindow
    });
  }

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: Scaffold(
        body: Container(
          width: double.infinity,
          height: double.infinity,
          color: kBgDark,
          child: Column(
            children: [
              // --- Persistent Header ---
              AppHeader(
                selectedCity: _selectedCity,
                availableCities: kAvailableCities,
                onCityChanged: _onCityChanged,
                isInChatView: _isInChatView,
                onLogoTap: () => setState(() {
                  _isInChatView = false;
                  _initialQuery = '';
                  _selectedPage = 'home'; // go back to main/home
                }),
                // new callback for an “About” button in header
                onAboutTap: () => setState(() => _selectedPage = 'about'),
              ),

              // --- Main Content (swaps only body, header stays) ---
              Expanded(
                child: AnimatedSwitcher(
                  duration: kTransitionDuration,
                  switchInCurve: Curves.easeInOut,
                  switchOutCurve: Curves.easeInOut,
                  child: _selectedPage == 'about'
                      ? AboutPage(onBack: () => setState(() => _selectedPage = 'home'))
                      : _isInChatView
                          ? _buildChatView(_initialQuery ?? '')
                          : _buildInitialSearchView(context),
                ),
              ),

              // --- Persistent footer ---
              const DisclaimerFooter(),
            ],
          ),
        ),

      ),
    );
  }

  Widget _buildInitialSearchView(BuildContext context) {
    return KeyedSubtree(
      key: const ValueKey('InitialView'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return SingleChildScrollView(
            padding: const EdgeInsets.only(bottom: 24),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight - 24),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 45),
                    const TitleText(),
                    const SizedBox(height: 15),
                    const Text(
                      "Ask about your city's bylaws like you'd ask a friend — we'll handle the search.",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.w400, fontSize: 18),
                    ),
                    const SizedBox(height: 30),
                    const InfoSection(),
                    const SizedBox(height: 40),
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [Colors.cyan.withAlpha(188), Colors.tealAccent.withAlpha(188)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 6, offset: Offset(0, 3))],
                      ),
                      child: ElevatedButton.icon(
                        onPressed: () => setState(() {
                          _isInChatView = true;
                          _initialQuery = '';
                        }),
                        //icon: const Icon(Icons.chat_bubble_outline_rounded),
                        label: const Text('Try it Now'),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 20),
                          textStyle: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
                          backgroundColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text("Always 100% free, No Signup", style: TextStyle(color: Colors.white.withAlpha(200), fontSize: 12)),
                    const SizedBox(height: 100),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildChatView(String initialQuery) {
    return KeyedSubtree(
      key: ValueKey('ChatView-${_selectedCity}-$_chatEpoch'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 0.0, vertical: 0.0),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: ChatWindow(
            key: ValueKey('ChatWindow-${_selectedCity}-$_chatEpoch'),
            initialQuery: initialQuery,
            selectedCity: _selectedCity,
          ),
        ),
      ),
    );
  }
}

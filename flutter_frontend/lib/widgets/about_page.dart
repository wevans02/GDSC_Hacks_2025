import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:url_launcher/url_launcher.dart';

// Match your existing color scheme
const Color kBgDark = Color(0xFF212121);
const Color kAccentColor = Color(0xFF00BCD4);
const Color kTextColor = Colors.white;

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBgDark,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: kTextColor),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(
          'About',
          style: GoogleFonts.poppins(
            color: kTextColor,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Section
            Center(
              child: Column(
                children: [
                  Icon(
                    Icons.gavel_rounded,
                    size: 64,
                    color: kAccentColor,
                  ).animate().scale(duration: 500.ms),
                  const SizedBox(height: 16),
                  ShaderMask(
                    shaderCallback: (bounds) => LinearGradient(
                      colors: [Colors.cyan, Colors.tealAccent],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ).createShader(bounds),
                    child: Text(
                      'Paralegal AI',
                      style: GoogleFonts.exo2(
                        fontSize: 36,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ).animate().fadeIn(delay: 200.ms, duration: 600.ms),
                  const SizedBox(height: 8),
                  Text(
                    'Making Municipal Bylaws Accessible to Everyone',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 16,
                      fontStyle: FontStyle.italic,
                    ),
                    textAlign: TextAlign.center,
                  ).animate().fadeIn(delay: 400.ms, duration: 600.ms),
                ],
              ),
            ),

            const SizedBox(height: 40),

            // Mission Section
            _buildSection(
              context,
              icon: Icons.lightbulb_outline,
              title: 'Our Mission',
              content:
                  'Municipal bylaws affect everyone—from parking regulations to noise ordinances—but they\'re often buried in dense legal documents. Paralegal AI uses advanced AI and Retrieval-Augmented Generation (RAG) to make this information accessible in plain language, helping residents understand their rights and obligations.',
              delay: 0,
            ),

            // How It Works Section
            _buildSection(
              context,
              icon: Icons.engineering_outlined,
              title: 'How It Works',
              content:
                  'We\'ve built a RAG system that indexes municipal bylaws from various Ontario cities. When you ask a question, our AI:\n\n'
                  '1. Searches through relevant bylaw documents\n'
                  '2. Retrieves the most relevant sections\n'
                  '3. Generates a clear, conversational answer\n'
                  '4. Provides source citations so you can verify the information',
              delay: 100,
            ),

            // Current Coverage
            _buildSection(
              context,
              icon: Icons.location_city,
              title: 'Current Coverage',
              content:
                  'We currently support bylaws from:\n\n'
                  '• Toronto\n'
                  '• Waterloo\n'
                  '• Guelph\n\n'
                  'More cities coming soon! Use the "Request a City" feature to let us know which municipality you\'d like to see next.',
              delay: 200,
            ),

            // Key Features
            _buildSection(
              context,
              icon: Icons.star_outline,
              title: 'Key Features',
              content:
                  '✓ 100% Free - No hidden costs, ever\n'
                  '✓ No Signup Required - Ask questions immediately\n'
                  '✓ Source Citations - Verify every answer\n'
                  '✓ Conversational Interface - Ask naturally\n'
                  '✓ Multi-City Support - Switch between municipalities\n'
                  '✓ PDF Links - Access original bylaw documents',
              delay: 300,
            ),

            // Important Disclaimer
            _buildSection(
              context,
              icon: Icons.warning_amber_outlined,
              title: 'Important Disclaimer',
              content:
                  'While we strive for accuracy, Paralegal AI is an informational tool and not a substitute for professional legal advice. Always verify critical information with official sources or consult a qualified legal professional for specific legal matters.',
              delay: 400,
              isWarning: true,
            ),

            // Tech Stack (Optional - can remove if too technical)
            _buildSection(
              context,
              icon: Icons.code,
              title: 'Built With',
              content:
                  'Flutter • Python • RAG (Retrieval-Augmented Generation) • Vector Databases • Natural Language Processing',
              delay: 500,
            ),

            // Contact Section
            _buildSection(
              context,
              icon: Icons.contact_mail_outlined,
              title: 'Get In Touch',
              content:
                  'Have feedback, questions, or want to request a city? We\'d love to hear from you!',
              delay: 600,
              trailing: Padding(
                padding: const EdgeInsets.only(top: 12.0),
                child: ElevatedButton.icon(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.add_location_alt),
                  label: const Text('Request a City'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: kAccentColor,
                    foregroundColor: Colors.black87,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 12,
                    ),
                  ),
                ),
              ),
            ),

            const SizedBox(height: 40),

            // Footer
            Center(
              child: Column(
                children: [
                  Text(
                    'Made with ❤️ for accessible legal information',
                    style: TextStyle(
                      color: Colors.white54,
                      fontSize: 12,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '© ${DateTime.now().year} Paralegal AI',
                    style: TextStyle(
                      color: Colors.white38,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 700.ms, duration: 600.ms),

            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String content,
    required int delay,
    bool isWarning = false,
    Widget? trailing,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isWarning
            ? Colors.orange.withOpacity(0.1)
            : Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isWarning
              ? Colors.orange.withOpacity(0.3)
              : Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                icon,
                color: isWarning ? Colors.orange : kAccentColor,
                size: 28,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.poppins(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: kTextColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            content,
            style: TextStyle(
              color: Colors.white.withOpacity(0.85),
              fontSize: 14,
              height: 1.6,
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    ).animate().fadeIn(delay: delay.ms, duration: 600.ms);
  }
}
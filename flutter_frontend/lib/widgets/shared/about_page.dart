import 'dart:convert';
import 'package:http/http.dart' as http;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../../core/constants.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key, this.onBack});

  final VoidCallback? onBack;

  Future<void> _launch(String url) async {
    final uri = Uri.parse(url);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }


  void _showFeedbackDialog(BuildContext context) {
    final feedbackController = TextEditingController();
    final emailController = TextEditingController();
    bool submitted = false;
    bool isSubmitting = false; // NEW


    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            if (submitted) {
              return Dialog(
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24)),
                insetPadding:
                    const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle,
                            color: Colors.cyan, size: 64),
                        const SizedBox(height: 16),
                        const Text(
                          "Thanks for your feedback!",
                          style: TextStyle(
                              fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          "We appreciate your input and will use it to improve the experience.",
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text("Close"),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }

            return Dialog(
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16)),
              insetPadding:
                  const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 500),
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        "Submit Feedback",
                        style: TextStyle(
                            fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: feedbackController,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: "Your feedback",
                          border: OutlineInputBorder(),
                        ),
                        inputFormatters: [
                          LengthLimitingTextInputFormatter(200),
                        ],
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: emailController,
                        decoration: const InputDecoration(
                          labelText: "Email (optional)",
                          border: OutlineInputBorder(),
                        ),
                        inputFormatters: [
                          LengthLimitingTextInputFormatter(50),
                        ],
                      ),
                      const SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: const Text("Cancel"),
                          ),
                          ElevatedButton(
                            onPressed: isSubmitting
                                ? null // disable during submit
                                : () async {
                                    final feedback = feedbackController.text.trim();
                                    final email = emailController.text.trim();

                                    if (feedback.isEmpty) return;

                                    setState(() => isSubmitting = true);

                                    try {
                                      final response = await http.post(
                                        Uri.parse("https://api.paralegalbylaw.org/api/feedback"),
                                        headers: {"Content-Type": "application/json"},
                                        body: jsonEncode({
                                          "feedback": feedback,
                                          "email": email.isNotEmpty ? email : null,
                                        }),
                                      );

                                      if (response.statusCode == 200) {
                                        setState(() {
                                          submitted = true;
                                          isSubmitting = false;
                                        });
                                      } else {
                                        setState(() => isSubmitting = false);
                                        _showError(context, "Something went wrong submitting feedback.");
                                      }
                                    } catch (e) {
                                      setState(() => isSubmitting = false);
                                      _showError(context, "Could not connect to server.");
                                    }
                                  },
                            child: isSubmitting
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                    ),
                                  )
                                : const Text("Submit"),
                          ),

                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final isWide = width >= 1080; // breakpoint for row vs column

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top bar: back arrow only (no "About" title)
          Row(
            children: [
              IconButton(
                tooltip: 'Back',
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
              ),
              const Spacer(),
            ],
          ),
          const SizedBox(height: 8),

          // Intro: headshot + text (Row on wide, Column on narrow)
          if (isWide)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Headshot larger
                ClipRRect(
                  borderRadius: BorderRadius.circular(150),
                  child: Image.asset(
                    'assets/images/cole_headshot.png',
                    width: 300,
                    height: 300,
                    fit: BoxFit.cover,
                  ),
                ),
                //const SizedBox(width: 28),
                // Text block with fixed max width for readability
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: _IntroText(onLaunch: _launch),
                ),
              ],
            )
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(100),
                  child: Image.asset(
                    'assets/images/cole_headshot.png',
                    width: 200,
                    height: 200,
                    fit: BoxFit.cover,
                  ),
                ),
                //const SizedBox(height: 16),
                _IntroText(onLaunch: _launch),
              ],
            ),

          const SizedBox(height: 36),
          Divider(color: Colors.white.withOpacity(0.16), thickness: 1),
          const SizedBox(height: 28),

          // How it works
          Text(
            "How It Works",
            style: GoogleFonts.poppins(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: kAccentColor, // solid teal; removed gradient
            ),
          ),
          const SizedBox(height: 12),
          Text(
            "Paralegal uses Retrieval-Augmented Generation (RAG). "
            "When you ask a question, it searches real city bylaw documents and municipal resources, "
            "then summarizes in plain language — grounded in the sources it found.\n\n"
            "Tap the sources under any answer to open the relevant bylaw page or PDF.",
            // "This makes it transparent and verifiable.",
            style: GoogleFonts.poppins(
              color: Colors.white.withOpacity(0.85),
              fontSize: 16,
              height: 1.6,
            ),
          ),

          const SizedBox(height: 32),
          Divider(color: Colors.white.withOpacity(0.16), thickness: 1),
          const SizedBox(height: 24),

          // Feedback button
          Text(
            "Feedback",
            style: GoogleFonts.poppins(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: kAccentColor,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            "Have suggestions or spotted an inaccuracy? I’d love to hear it.",
            style: GoogleFonts.poppins(
              color: Colors.white.withOpacity(0.85),
              fontSize: 16,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 14),
          ElevatedButton.icon(
            onPressed: () => _showFeedbackDialog(context),
            icon: const Icon(Icons.feedback_outlined),
            label: const Text("Submit Feedback"),
            style: ElevatedButton.styleFrom(
              backgroundColor: kAccentColor,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
            ),
          ),

          const SizedBox(height: 48),
          Center(
            child: Text(
              "© 2025 Paralegal AI — Built with Flutter & Python",
              style: GoogleFonts.poppins(color: Colors.white.withOpacity(0.5), fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

class _IntroText extends StatelessWidget {
  const _IntroText({required this.onLaunch});
  final Future<void> Function(String url) onLaunch;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Title (solid teal)
        Text(
          "About",
          style: GoogleFonts.poppins(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            color: kAccentColor,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          "Hi, I’m Cole, A Computer Science Student at the University of Guelph.\n\n"
          "Starting as a hackathon project with teammates from U of Guelph, I built Paralegal AI to help make city bylaws readable and searchable by everyone.\n\n"
          "It’s powered by modern AI retrieval tech, but focused on clarity and accessibility. Just ask it a question and you'll get a straightforward answer, citing the bylaws that it read to form its answer.\n\n",
          // "I hope this helps you understand your city’s rules a little better.",
          style: GoogleFonts.poppins(
            color: Colors.white.withOpacity(0.88),
            fontSize: 16,
            height: 1.6,
          ),
        ),
        const SizedBox(height: 18),

        // Socials row with real brand icons
        Wrap(
          spacing: 12,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            _SocialIconButton(
              icon: FontAwesomeIcons.github,
              label: "GitHub",
              onTap: () => onLaunch("https://github.com/colewesterveld"),
            ),
            _SocialIconButton(
              icon: FontAwesomeIcons.linkedin,
              label: "LinkedIn",
              onTap: () => onLaunch("https://www.linkedin.com/in/cole-westerveld/"),
            ),
            _SocialIconButton(
              icon: Icons.mail_outline,
              label: "Email",
              onTap: () => onLaunch("mailto:colewesterveld@gmail.com"),
            ),
          ],
        ),
      ],
    );
  }
}

class _SocialIconButton extends StatelessWidget {
  const _SocialIconButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.10)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: kAccentColor, size: 18),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(color: Colors.white)),
          ],
        ),
      ),
    );
  }
}

void _showError(BuildContext context, String msg) {
  showDialog(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text("Error"),
      content: Text(msg),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text("OK"),
        ),
      ],
    ),
  );
}
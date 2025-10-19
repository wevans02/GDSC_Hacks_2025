import 'package:flutter/material.dart';
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

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final isWide = width >= 760; // breakpoint for row vs column

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
                  borderRadius: BorderRadius.circular(20),
                  child: Image.asset(
                    'assets/images/cole_headshot.png',
                    width: 220,
                    height: 220,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(width: 28),
                // Text block with fixed max width for readability
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: _IntroText(onLaunch: _launch),
                ),
              ],
            )
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.asset(
                    'assets/images/cole_headshot.png',
                    width: 200,
                    height: 200,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 16),
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
            "Paralegal AI uses Retrieval-Augmented Generation (RAG). "
            "When you ask a question, it searches real city bylaw documents and municipal resources, "
            "then summarizes in plain language — grounded in the sources it found.\n\n"
            "Tap the source chips under any answer to open the bylaw page or PDF. "
            "This makes it transparent and verifiable.",
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
            onPressed: () => _launch("https://your-feedback-form-link.com"),
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
          "Hi, I’m Cole 👋 — I built Paralegal AI to help make city bylaws readable and searchable by everyone.\n\n"
          "It’s powered by modern AI retrieval tech, but focused on clarity and accessibility, not hype.\n\n"
          "I hope this helps you understand your city’s rules a little better.",
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

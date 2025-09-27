// widgets/about_page.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('About Paralegal AI'),
          centerTitle: true,
        ),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.blueGrey[900]?.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withOpacity(0.1), width: 1.5),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: SelectionArea(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Header
                        Row(
                          children: [
                            Icon(Icons.gavel, color: Colors.cyanAccent.shade100),
                            const SizedBox(width: 12),
                            Text(
                              'Paralegal AI',
                              style: GoogleFonts.exo2(
                                fontSize: 28,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.1,
                              ),
                            ),
                            const Spacer(),
                            TextButton.icon(
                              onPressed: () => _launchUrl(context, 'https://paralegalbylaw.org'),
                              icon: const Icon(Icons.open_in_new),
                              label: const Text('Website'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Mission',
                          style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Make municipal bylaws easy to find and understand for everyone. '
                          'We index public bylaws and use retrieval-augmented generation (RAG) to surface relevant sections quickly.',
                          style: const TextStyle(height: 1.5),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'How it works',
                          style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          '• Search across curated municipal bylaw sources.\n'
                          '• Read summarized answers, with citations back to the source documents.\n'
                          '• Ask follow-ups to refine the answer.',
                          style: TextStyle(height: 1.5),
                        ),
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.black.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.white.withOpacity(0.08)),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: const [
                              Icon(Icons.info_outline),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Paralegal AI is not a law firm and does not provide legal advice. '
                                  'Always consult a qualified legal professional for your specific situation.',
                                  style: TextStyle(fontSize: 13, height: 1.4),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            OutlinedButton.icon(
                              onPressed: () => _launchUrl(context, 'mailto:colewesterveld@gmail.com'),
                              icon: const Icon(Icons.mail_outline),
                              label: const Text('Contact'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => _launchUrl(context, 'https://github.com/colewesterveld'),
                              icon: const Icon(Icons.code),
                              label: const Text('GitHub'),
                            ),
                          ],
                        )
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  static Future<void> _launchUrl(BuildContext context, String urlString) async {
    final uri = Uri.parse(urlString);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open link: $urlString')),
      );
    }
  }
}

// widgets/disclaimer.dart
import 'package:flutter/material.dart';

class DisclaimerFooter extends StatelessWidget {
  const DisclaimerFooter({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.3),
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.1),
            width: 1,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          
          Text(
            'This AI assistant provides information for research purposes only and is not a substitute for professional legal advice. '
            'Responses may contain errors or be incomplete. Always verify information with official sources and consult with a qualified legal professional for specific legal matters. '
            'The creators are not responsible for any decisions made based on this information.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 11,
              height: 1.4,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '© 2024 Paralegal AI • ',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.4),
                  fontSize: 10,
                ),
              ),
              GestureDetector(
                onTap: () => _showFullDisclaimer(context),
                child: Text(
                  'View Full Terms',
                  style: TextStyle(
                    color: Colors.cyan.withOpacity(0.7),
                    fontSize: 10,
                    decoration: TextDecoration.underline,
                    decorationColor: Colors.cyan.withOpacity(0.7),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showFullDisclaimer(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => _FullDisclaimerDialog(),
    );
  }
}

class _FullDisclaimerDialog extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: BoxConstraints(maxWidth: 800, maxHeight: 600),
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Colors.white.withOpacity(0.2),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 20,
              offset: Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.3),
                borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                border: Border(
                  bottom: BorderSide(
                    color: Colors.white.withOpacity(0.1),
                    width: 1,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.gavel_rounded,
                    color: Colors.orange,
                    size: 24,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Terms of Use & Disclaimer',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: Icon(
                      Icons.close,
                      color: Colors.white.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
            
            // Content
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSection(
                      "TLDR; Don't do something stupid and blame me, pls n thx🙏",
                      titleSize: 16
                    ),
                    _buildSection(
                      'Not Legal Advice',
                      content: 'This application is an informational tool only. It does not provide legal advice, legal opinions, or legal services. The information provided should not be used as a substitute for competent legal advice from a licensed attorney in your jurisdiction.',
                    ),
                    _buildSection(
                      'AI-Generated Content',
                      content: 'Responses are generated by artificial intelligence and may contain errors, inaccuracies, or incomplete information. Always verify information against official sources and current legal documents.',
                    ),
                    _buildSection(
                      'No Attorney-Client Relationship',
                      content: 'Use of this application does not create an attorney-client relationship. Do not send confidential or sensitive information through this system.',
                    ),
                    _buildSection(
                      'Information Currency',
                      content: 'While we strive to maintain current information, laws and regulations change frequently. Always consult the most recent official sources for the latest legal requirements.',
                    ),
                    _buildSection(
                      'Limitation of Liability',
                      content: 'The creators and operators of this application are not liable for any decisions made or actions taken based on information provided by this system.',
                    ),
                    _buildSection(
                      'Professional Consultation',
                      content: 'For specific legal matters, complex situations, or important decisions, always consult with a qualified legal professional who can provide advice tailored to your specific circumstances.',
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(String title, {String? content, double titleSize = 14, double descSize = 12}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: Colors.white,
              fontSize: titleSize,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          if (content != null)
            Text(
              content,
              style: TextStyle(
                color: Colors.white.withOpacity(0.8),
                fontSize: descSize,
                height: 1.5,
              ),
            ),
        ],
      ),
    );
  }
}
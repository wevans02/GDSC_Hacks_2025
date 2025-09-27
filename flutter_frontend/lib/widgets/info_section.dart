// widgets/info_section.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:ui';

class InfoSection extends StatelessWidget {
  const InfoSection({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(maxWidth: 1000),
      child: Column(
        children: [
          // Main explanation
          //_buildMainExplanation(),
          const SizedBox(height: 24),
          
          // Feature cards
          _buildFeatureCards(),
          const SizedBox(height: 20),
          
          // Trust indicators
          //_buildTrustIndicators(),
        ],
      ),
    );
  }

  Widget _buildMainExplanation() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.15),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.cyan.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.search_rounded,
                  color: Colors.cyan,
                  size: 24,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Instant Municipal Law Search',
                  style: GoogleFonts.exo2(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Get immediate answers about local bylaws, regulations, and municipal codes. Our AI searches through official documents to provide accurate, source-backed responses to your legal questions.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.85),
              fontSize: 15,
              height: 1.5,
            ),
            textAlign: TextAlign.left,
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureCards() {
    final features = [
      {
        'icon': Icons.library_books_outlined,
        'title': 'Official Sources',
        'desc': 'All answers backed and cited to official municipal records',
      },
      {
        'icon': Icons.speed_rounded,
        'title': 'Instant Results',
        'desc': 'Get answers in seconds, not hours',
      },
      {
        'icon': Icons.chat_bubble_outline,
        'title': 'Natural Language',
        'desc': 'Informed through conversation, supports most languages',
      },
    ];

    return Row(
      children: features.map((feature) {
        return Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.all(24),
            // decoration: BoxDecoration(
              //color: Colors.white.withOpacity(0.05),
              // borderRadius: BorderRadius.circular(12),
              // border: Border.all(
              //   color: Colors.white.withOpacity(0.1),
              //   width: 1,
              // ),
            // ),
            child: Column(
              children: [
                Icon(
                  feature['icon'] as IconData,
                  color: Colors.cyan.withOpacity(0.8),
                  size: 28,
                ),
                const SizedBox(height: 8),
                Text(
                  feature['title'] as String,
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 18,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  feature['desc'] as String,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 14,
                    //height: 1.3,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildTrustIndicators() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _buildTrustBadge(
          Icons.verified_outlined,
          'Verified Sources',
          Colors.green.withOpacity(0.8),
        ),
        const SizedBox(width: 20),
        _buildTrustBadge(
          Icons.update_rounded,
          'Always Current',
          Colors.blue.withOpacity(0.8),
        ),
        const SizedBox(width: 20),
        _buildTrustBadge(
          Icons.security_rounded,
          'Secure & Private',
          Colors.purple.withOpacity(0.8),
        ),
      ],
    );
  }

  Widget _buildTrustBadge(IconData icon, String label, Color color) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: color.withOpacity(0.2),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            icon,
            color: color,
            size: 18,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
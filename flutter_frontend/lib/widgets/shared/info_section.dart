// widgets/info_section.dart
import 'package:flutter/material.dart';



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
          _buildFeatureCards(context),
          const SizedBox(height: 20),
          
          // Trust indicators
          //_buildTrustIndicators(),
        ],
      ),
    );
  }

  

  Widget _buildFeatureCards(BuildContext context) {
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

    // adjustable cutoff for when to switch layout
    const cutoff = 600.0; 

    final isNarrow = MediaQuery.of(context).size.width < cutoff;

    if (isNarrow) {
      // Column layout for phones
      return Column(
        children: features.map((feature) {
          return Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.all(24),
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
                  style: const TextStyle(
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
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          );
        }).toList(),
      );
    } else {
      // Row layout for larger screens
      return Row(
        children: features.map((feature) {
          return Expanded(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.all(24),
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
                    style: const TextStyle(
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
  }


  
}
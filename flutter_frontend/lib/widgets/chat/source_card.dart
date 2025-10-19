import 'package:flutter/material.dart';

class SourceCard extends StatelessWidget {
  const SourceCard({super.key, required this.source, this.onTap});

  final Map<String, dynamic> source;
  final VoidCallback? onTap;

  bool get _isPdf {
    final url = (source['pdf_url'] ?? '').toString().toLowerCase();
    return url.endsWith('.pdf') || url.contains('.pdf?');
  }

  String get _faviconUrl {
    final raw = (source['pdf_url'] ?? source['url'] ?? '').toString();
    final uri = Uri.tryParse(raw);
    final domain = (uri?.host.isNotEmpty ?? false) ? uri!.host : raw;
    return 'https://www.google.com/s2/favicons?sz=128&domain_url=$domain';
  }

  @override
  Widget build(BuildContext context) {
    final String title = (source['title'] ?? 'Source').toString();
    final String page = (source['page_numbers'] ?? '').toString().trim();
    final String bylawId = (source['bylaw_id'] ?? '').toString();
    final displaySubtitle = [
      if (bylawId.isNotEmpty) bylawId.replaceFirst('Chapter ', ''),
      if (page.isNotEmpty) page,
    ].join(' • ');

    return SizedBox(
      width: 220,
      child: Material(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(16),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          splashColor: Colors.white.withOpacity(0.08),
          highlightColor: Colors.white.withOpacity(0.04),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 90,
                width: double.infinity,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xAA00BCD4), Color(0x6640E0D0)],
                        ),
                      ),
                    ),
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.all(10.0),
                        child: Image.network(
                          _faviconUrl,
                          width: 44,
                          height: 44,
                          errorBuilder: (_, __, ___) => Icon(
                            _isPdf ? Icons.picture_as_pdf_rounded : Icons.public_rounded,
                            size: 40,
                            color: Colors.white.withOpacity(0.9),
                          ),
                        ),
                      ),
                    ),
                    if (_isPdf)
                      Positioned(
                        top: 8,
                        right: 8,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.black.withOpacity(0.35),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Text(
                            'PDF',
                            style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.3),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                    if (displaySubtitle.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        displaySubtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.8)),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import '../../core/constants.dart';
import 'source_card.dart';

class _DragScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.stylus,
        PointerDeviceKind.invertedStylus,
        PointerDeviceKind.unknown,
      };
}

class SourcesStrip extends StatefulWidget {
  const SourcesStrip({super.key, required this.sources, required this.onOpenUrl});

  final List<Map<String, dynamic>> sources;
  final void Function(String url) onOpenUrl;

  @override
  State<SourcesStrip> createState() => _SourcesStripState();
}

class _SourcesStripState extends State<SourcesStrip> {
  final _ctrl = ScrollController();

  static const double _cardWidth = 220;
  static const double _cardGap = 10;
  static const double _cardHeight = 150;

  bool _canLeft = false;
  bool _canRight = false;

  @override
  void initState() {
    super.initState();
    _ctrl.addListener(_updateCanScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) => _updateCanScroll());
  }

  @override
  void dispose() {
    _ctrl.removeListener(_updateCanScroll);
    _ctrl.dispose();
    super.dispose();
  }

  void _updateCanScroll() {
    if (!mounted || !_ctrl.hasClients) return;
    final pos = _ctrl.position;
    final left = pos.extentBefore > 2;
    final right = pos.extentAfter > 2;
    if (left != _canLeft || right != _canRight) {
      setState(() {
        _canLeft = left;
        _canRight = right;
      });
    }
  }

  Future<void> _scrollBy(double delta) async {
    if (!_ctrl.hasClients) return;
    final pos = _ctrl.position;
    final target = (pos.pixels + delta).clamp(pos.minScrollExtent, pos.maxScrollExtent);
    await _ctrl.animateTo(target, duration: const Duration(milliseconds: 260), curve: Curves.easeOutCubic);
  }

  @override
  Widget build(BuildContext context) {
    final sourcesToDisplay = widget.sources.take(8).toList();
    final double pageDelta = 3 * (_cardWidth + _cardGap);

    return Padding(
      padding: const EdgeInsets.only(top: 10.0, left: 32.0),
      child: SizedBox(
        height: _cardHeight,
        child: Stack(
          children: [
            ScrollConfiguration(
              behavior: _DragScrollBehavior(),
              child: ListView.separated(
                controller: _ctrl,
                scrollDirection: Axis.horizontal,
                physics: const ClampingScrollPhysics(),
                itemCount: sourcesToDisplay.length,
                separatorBuilder: (_, __) => const SizedBox(width: _cardGap),
                itemBuilder: (context, i) {
                  final src = sourcesToDisplay[i];
                  return SourceCard(
                    source: src,
                    onTap: () {
                      final url = (src['pdf_url'] ?? src['url'] ?? '').toString();
                      if (url.isNotEmpty) widget.onOpenUrl(url);
                    },
                  );
                },
              ),
            ),
            // Left arrow
            Positioned(
              left: 0,
              top: 0,
              bottom: 0,
              child: AnimatedOpacity(
                opacity: _canLeft ? 1 : 0,
                duration: const Duration(milliseconds: 180),
                child: Center(
                  child: _NavButton(icon: Icons.arrow_back_ios_new_rounded, onTap: _canLeft ? () => _scrollBy(-pageDelta) : null),
                ),
              ),
            ),
            // Right arrow
            Positioned(
              right: 0,
              top: 0,
              bottom: 0,
              child: AnimatedOpacity(
                opacity: _canRight ? 1 : 0,
                duration: const Duration(milliseconds: 180),
                child: Center(
                  child: _NavButton(icon: Icons.arrow_forward_ios_rounded, onTap: _canRight ? () => _scrollBy(pageDelta) : null),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({required this.icon, this.onTap});

  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black.withOpacity(0.6),
      shape: const CircleBorder(),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: SizedBox(
          width: 36,
          height: 36,
          child: Icon(icon, size: 18, color: onTap == null ? Colors.white30 : Colors.white),
        ),
      ),
    );
  }
}

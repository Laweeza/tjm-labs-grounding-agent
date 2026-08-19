# Design Document: 

## Assumptions
- Target: Windows 11, single monitor, 1920 x 1080 display resolution
- Notepad desktop shortcut exists before script is run
- Access to jsonplaceholder.typicode.com, no auth required
- "Close Notepad" Action = save first, close via standard window closing control
- No concurrent user interaction with desktop during run
- Save post in tjm-project directory on Desktop
- Grounding is repeated for every post, to re-screenshot and re-ground before each launch.

## System Design
![Diagram](screenshots\designchart.png)

 Each iteration screenshots and re-grounds from scratch rather than caching the location of the icon/text. Cannot assume that the icon position will be stable.

## Grounding Strategy

Results from the ScreenSpot-Pro: GUI Grounding for Professional High-Resolution Computer Use found that even the simplest method, ReGround, yields large accurary gains over a single grounding pass (18.9% -> 40.2% on OS-Atlas-7B).

This project uses a single ReGround pass + VLM-based grounder

1. **Coase pass**: full desktop screenshot sent to vision-language model with natural language instruction("locate Notepad icon"). Model is reasoning about the instruction semantically, not pixel matching.

2. Fixed crop (1024 x 1024 per research paper ablation) which is then re-sent to model to refine coordinate. The target should now occupy a larger fraction of the cropped image, and the prediction becomes more precise.

3. Coordinates from the refined crop are mapped back to the screen and returned as a click target.

## Had to resize d/t anthropic scaling


bonus
popup handling - tbd - uses same grounding mechanism. before each lick a query checks for dialogue - model to locate dismiss...


## Tradeoffs
- ReGround uses a single crop and reground pass, with fixed size of 1024x1024, I chose to go this route rather than elaborate methods, for these reasons:

- **Cost Scaling** - ScreenSeekeR requires planner call, multiple grounder calls, scoring+recursion loop and probably at least 10-20 model calls for a grounding operation. This results in multiple grounding cycles and could add minutes more of latency and higher API cost.

- **Accurary** - Per the reference paper, ScreenSeekeR improves over ReGround by ~8 points on ScreenSpot-Pro - benchmark of dense progfessional software. A single notepad icon is an easier search problem; accuracy gap not worth it.

**Limitation of this choice** ReGround does a single crop on coarse prediction, but unlike Iterative Narrowing, which re-centers across multiple rounds, it only gets one attempt. If the pass is far off, the target falls outside even on a correctly centered crop and there is no subsequent round to recover. To handle this risk without having to implement a heavier iterative method, the pass is gated by confidence: if returns low confidence or no target, the system falls back to a fresh full image grounding attempt.


## Error Handling
- Low confidence in finding the target wth screenshot
- Clicking lands on wrong target, retry?
- API fetch issues
- How to handle other icons/popups
- Save issues

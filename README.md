This is the code used in the Rage Mysterequinox Iron Puzzler event to produce the puzzle Rage of the Quebecats.

## Code Organization

This is very hacky code. I make no promises that it works well. This is a slightly cleaned up version. The even-hackier version which was originally used is in `lasercats_code_old.py`

To get a randomly generated puzzle, run `lasercats.py`.

## Puzzle Rules
*From the original puzzle's intro text*

You and your pet human Jean-François are trapped by the Quebecois Guard in a 5x5 square room. Awaiting rescue, your human decides to torment you with the uncatchable-tiny-red-dot-mouse. However, lacking his laser pointer, he’s using a laser rangefinder he borrowed from the Quebecois Liberation Front. 

Unfortunately, you've been trapped in a carnival funhouse full of double-sided diagonal mirrors. It’s dark and Jean-François can’t see anything, so he stands in the center of the room (there's no mirror in the center of the room) and fires his laser. The rangefinder lets him know how far the laser traveled before hitting the wall. You pounce on the spot where it landed, but too late! You'll need to use your advanced optics skills to ascertain where it will show up next before he fires.

Also, his rangefinder is a bit overpowered and instantly knocks any mirror it hits 90 degrees around on its swivel. If the same beam hits the same mirror a second time, it’s already been rotated once by the first hit, and the second hit rotates it again.

Jean-François starts each room by firing his laser directly to the north, then east, then south and west and back to north and so on. Humans are important for producing lasers, but otherwise irrelevant and, in particular, transparent.

The PosNeg plugin maintains a database of positive/negative
actions that can be directed at one or more "targets".

An action is in the form of a string with one or more placeholders of
the form "{0}", "{1}", etc.  When applied to a target they are matched
in order.  For example, if the action

  pushes {0} into {1}

is applied to two targets "A" and "B" will result in

  * BOT pushes A into B

The database of possible actions can be modified in-channel.

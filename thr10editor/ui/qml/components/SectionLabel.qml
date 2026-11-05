import QtQuick
import QtQuick.Controls.Basic
import THR10

// Подпись раздела капсом.
Label {
    font.pixelSize: Theme.fontSize.xs
    font.weight: Theme.weight.semibold
    font.letterSpacing: Theme.letterSpacing.caps
    color: Theme.c.textFaint
    text: ""
    Component.onCompleted: text = text.toUpperCase()
}

#!/bin/bash
# Compile ArchUnitRunner.java with proper classpath

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build classpath from all JARs in lib directory
CLASSPATH=""
for jar in "$SCRIPT_DIR"/lib/*.jar; do
    if [ -z "$CLASSPATH" ]; then
        CLASSPATH="$jar"
    else
        CLASSPATH="$CLASSPATH:$jar"
    fi
done

# Compile the Java file
echo "Compiling ArchUnitRunner.java..."
echo "Classpath: $CLASSPATH"
javac -cp "$CLASSPATH" "$SCRIPT_DIR/ArchUnitRunner.java"

if [ $? -eq 0 ]; then
    echo "✅ Compilation successful!"
else
    echo "❌ Compilation failed!"
    exit 1
fi

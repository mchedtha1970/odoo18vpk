/** @odoo-module **/

const { DateTime } = luxon;

export const BE_OFFSET = 543;
const FLAG = "__vpkBuddhistDate";

/**
 * Formats used to talk to the server or to build keys (ISO / SQL like
 * "yyyy-MM-dd") must stay in the Gregorian calendar.
 */
export function isMachineFormat(fmt) {
    if (typeof fmt !== "string") {
        return true;
    }
    return /^\s*y+[-/]?M/.test(fmt) || fmt.includes("'T'");
}

function splitFormat(fmt) {
    const parts = [];
    let literal = false;
    let current = "";
    for (const char of fmt) {
        if (char === "'") {
            if (current) {
                parts.push({ literal, text: current });
            }
            current = "";
            literal = !literal;
            continue;
        }
        current += char;
    }
    if (current) {
        parts.push({ literal, text: current });
    }
    return parts;
}

function buddhistFormat(fmt, year) {
    const beYear = year + BE_OFFSET;
    return splitFormat(fmt)
        .map((part) => {
            if (part.literal) {
                return `'${part.text}'`;
            }
            return part.text.replace(/y+/g, (token) => {
                if (token.length === 2) {
                    return `'${String(beYear % 100).padStart(2, "0")}'`;
                }
                return `'${beYear}'`;
            });
        })
        .join("");
}

if (!DateTime.prototype[FLAG]) {
    const originalToFormat = DateTime.prototype.toFormat;
    const originalToLocaleString = DateTime.prototype.toLocaleString;
    const originalFromFormat = DateTime.fromFormat;

    DateTime.prototype.toFormat = function (fmt, opts) {
        if (!this.isValid || isMachineFormat(fmt) || !/y/.test(fmt.replace(/'[^']*'/g, ""))) {
            return originalToFormat.call(this, fmt, opts);
        }
        return originalToFormat.call(this, buddhistFormat(fmt, this.year), opts);
    };

    DateTime.prototype.toLocaleString = function (formatOpts, opts) {
        if (!this.isValid) {
            return originalToLocaleString.call(this, formatOpts, opts);
        }
        return originalToLocaleString.call(
            this.reconfigure({ outputCalendar: "buddhist" }),
            formatOpts,
            opts
        );
    };

    DateTime.fromFormat = function (text, fmt, opts) {
        const result = originalFromFormat.call(this, text, fmt, opts);
        if (result.isValid && !isMachineFormat(fmt) && result.year >= 2400) {
            return result.minus({ years: BE_OFFSET });
        }
        return result;
    };

    DateTime.prototype[FLAG] = true;
}

using System.Collections.Generic;

namespace MatchEngine.Core.Engine.Commentary;

public interface ICommentRepository
{
    IEnumerable<string> Get(string locale, string tone, string eventType);
}

use std::collections::VecDeque;

#[derive(Clone)]
pub struct Tee<T> {
    queue: VecDeque<T>,
    leader: TeeConsumer,
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum TeeConsumer {
    A,
    B,
}

pub type TeeResult<'a, T> = Result<T, TeeEmptyError<'a, T>>;

#[must_use]
pub struct TeeEmptyError<'a, T> {
    tee: &'a mut Tee<T>,
    consumer: TeeConsumer,
}

impl<T> Default for Tee<T> {
    fn default() -> Self {
        Self {
            queue: VecDeque::new(),
            leader: TeeConsumer::A,
        }
    }
}

impl<T> Tee<T> {
    pub fn next(&mut self, consumer: TeeConsumer) -> TeeResult<T> {
        (self.leader != consumer)
            .then(|| self.queue.pop_front())
            .flatten()
            .ok_or(TeeEmptyError {
                tee: self,
                consumer,
            })
    }

    pub fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }
}

impl<'a, T> TeeEmptyError<'a, T> {
    pub fn provide_next(self, value: T) {
        self.tee.leader = self.consumer;
        self.tee.queue.push_back(value);
    }
}
